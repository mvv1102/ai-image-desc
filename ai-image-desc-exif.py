import base64
import json
import os
import sys
import time
from exif import Image as ExifImage
import asyncio
from ollama import AsyncClient
from ollama import GenerateResponse

from argparse import ArgumentParser
from pathlib import Path

async def generate_ollama_response(img_base64, model) -> GenerateResponse:
    response = await AsyncClient().generate(
        model=model,
        format="json",
        prompt="Describe the photo as a subject and a collection of keywords. Return the response in JSON format. Use the following schema: { subject: string, keywords: string[] }",
        images=[img_base64],
        options={"temperature": 0.3}  # Lower temperature for more consistent output
    )
    return response

async def ask_llm_file(path, update_exif, output_path, model, timeout):
    print(f"Processing file {path} using {model}")

    with open(path, 'rb') as img_file:
        img_data = img_file.read()

        # Convert image to base64 for Ollama
        img_base64 = base64.b64encode(img_data).decode('utf-8')

        try:
            response = await asyncio.wait_for(generate_ollama_response(img_base64, model), timeout=timeout)
        except asyncio.TimeoutError:
            print(f"Timeout while generating response for {path}")
            return False

        if update_exif:
            return update_file(path, response['response'], output_path) # return True if successful, False otherwise
        else:
            print(response['response'])
    return True

def update_file(file_path, description_json, output_path):
    if output_path is None:
        filename, extension = os.path.splitext(file_path)
        output_path = filename + "_edited" + extension
    else:
        if not os.path.isabs(output_path):
            output_path = os.path.join(os.path.dirname(file_path), output_path)
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        output_path = os.path.normpath(os.path.join(output_path, os.path.basename(file_path)))

    print(f"Updating file: {output_path}")
    try:
        with open(file_path, "rb") as img_file:
            img = ExifImage(img_file)
            if description_json is not None:
                data = json.loads(description_json)
                description = f"{data['subject']} ({', '.join(data['keywords'])})".encode('ascii', 'backslashreplace').decode('ascii')
                print(f"Setting description: {description}")
                img.image_description = description

            with open(output_path, "wb") as ofile:
                ofile.write(img.get_file())
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return False
    return True

def ask_llm(path: Path, *, update_exif=False, output_path=None, model="gemma3:latest", timeout=60):
    start_time = time.time()
    count = 0
    failed = []
    if path.is_file():
        success = asyncio.run(ask_llm_file(path, update_exif, output_path, model, timeout))
        if not success:
            failed.append(path)
        count += 1
    else:
        if not path.is_absolute():
            path = path.resolve()
            
        images = []
        for pattern in ["*.jpg", "*.png", "*.tif", "*.bmp"]:
            images += path.glob(pattern, case_sensitive=False)

        for image in images:
            file_path = path / image
            if file_path.is_file():
                success = asyncio.run(ask_llm_file(file_path, update_exif, output_path, model, timeout))
                if not success:
                    failed.append(file_path)
                count += 1
    end_time = time.time()
    print(f"Total images processed: {count}")
    if len(failed) > 0:
        print(f"Failed to process {len(failed)} images: {failed}")
    print(f"Total run time: {end_time - start_time:.2f} seconds")

def update_files(args):
    ask_llm(args.path, update_exif=True, output_path=args.output, model=args.model, timeout=args.timeout)

def ask_files(args):
    ask_llm(args.path, model=args.model, timeout=args.timeout)

if __name__ == "__main__":
    default_model = "gemma3:latest"
    default_timeout = 180
    
    parser = ArgumentParser(prog=sys.argv[0], description="AI assisted image description tool")

    # Adding common CLI arguments
    common_parser = ArgumentParser(add_help=False)
    common_parser.add_argument("path", type=Path, default=Path("."), help="Where to start the search")
    common_parser.add_argument("--model", "-m", default=default_model, help=f"Model to use, default is '{default_model}'")
    common_parser.add_argument("--timeout", "-t", default=default_timeout, type=int, help=f"Timeout for LLM requests in seconds, default is {default_timeout} seconds")

    # Subcommands
    commands = parser.add_subparsers(help="Commands")

    update = commands.add_parser("update", parents=[common_parser], help="Updates exif metadata of the image files with generated descriptions")
    update.add_argument("--output", "-o", help="Output path; if not specified, will create a new file with '_edited' suffix")
    update.set_defaults(func=update_files)

    ask = commands.add_parser("ask", parents=[common_parser], help="Dry mode. Finds and labels the images but won't update exif metadata")
    ask.set_defaults(func=ask_files)

    args = parser.parse_args()

    if "func" in args:
        args.func(args)
    elif not ("-h" in args or "--help" in args):
        parser.print_help()
        sys.exit(1)
