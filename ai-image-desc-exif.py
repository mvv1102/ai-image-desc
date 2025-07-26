import base64
import json
import glob
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

async def ask_llm_file(path, update_exif, output_path, model):
    print(f"Processing file {path} using {model}")

    with open(path, 'rb') as img_file:
        img_data = img_file.read()

        # Convert image to base64 for Ollama
        img_base64 = base64.b64encode(img_data).decode('utf-8')

        try:
            response = await asyncio.wait_for(generate_ollama_response(img_base64, model), timeout=180)
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

def ask_llm(path: Path, *, update_exif=False, output_path=None, model="gemma3:latest"):
    start_time = time.time()
    count = 0
    failed = []
    if path.is_file():
        success = asyncio.run(ask_llm_file(path, update_exif, output_path, model))
        if not success:
            failed.append(path)
        count += 1
    else:
        images = []
        for pattern in ["*.jpg", "*.png", "*.tif", "*.bmp"]:
            images += path.glob(pattern, case_sensitive=False)

        for image in images:
            file_path = path / image
            if file_path.is_file():
                success = asyncio.run(ask_llm_file(file_path, update_exif, output_path, model))
                if not success:
                    failed.append(file_path)
                count += 1
    end_time = time.time()
    print(f"Total images processed: {count}")
    if len(failed) > 0:
        print(f"Failed to process {len(failed)} images: {failed}")
    print(f"Total run time: {end_time - start_time:.2f} seconds")

def update_files(args):
    ask_llm(args.path, update_exif=True, output_path=args.output, model=args.model)

def ask_files(args):
    ask_llm(args.path, model=args.model)

if __name__ == "__main__":
    parser = ArgumentParser(prog=sys.argv[0], description="AI assisted image description tool")
    # Adding global CLI arguments
    parser.add_argument("--model", "-m", default="gemma3:latest", help="Model to use")

    # Subcommands
    commands = parser.add_subparsers(help="Commands")

    update = commands.add_parser("update", help="Updates image files")
    update.add_argument("path", type=Path,  help="Where to start the search")
    update.add_argument("--output", "-o", help="Output path")
    update.set_defaults(func=update_files)

    ask = commands.add_parser("ask", help="Dry mode. Finds and labels the images but won't update exif metadata")
    ask.add_argument("path", type=Path,  help="Where to start the search")
    ask.set_defaults(func=ask_files)

    args = parser.parse_args()
    if "func" in args:
        args.func(args)
    else:
        parser.print_help()
        sys.exit(1)
