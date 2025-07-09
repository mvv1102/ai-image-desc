import base64
import json
import os
import glob
import sys
from datetime import datetime
from exif import Image as ExifImage
from exif import DATETIME_STR_FORMAT
import ollama
from ollama import chat
from ollama import ChatResponse


EXIF_TAGS = [
    "author",
    "artist",
    "copyright",
    "make",
    "model",
    "datetime",
    "datetime_original",
    "datetime_digitized",
    "image_description",
    "gps_version_id",
    "gps_latitude_ref",
    "gps_latitude",
    "gps_longitude_ref",
    "gps_longitude",
    "gps_altitude_ref",
    "gps_altitude",
    "user_comment",
]

def ask_llm(folder, update_exif=False, output_path=None):
    if os.path.isfile(folder):
        file = os.path.basename(folder)
        file_path = folder
        ask_llm_file(file_path, update_exif, output_path)
    else:
        images = glob.glob(os.path.join(folder, "*.[jJ][pP][gG]")) + \
            glob.glob(os.path.join(folder, "*.[pP][nN][gG]")) + \
            glob.glob(os.path.join(folder, "*.[tT][iI][fF]")) + \
            glob.glob(os.path.join(folder, "*.[bB][mM][pP]"))
        for file in images:
            file_path = os.path.join(folder, file)
            if os.path.isfile(file_path):
                ask_llm_file(file_path, update_exif, output_path)

def ask_llm_file(path, update_exif=False, output_path=None):
    print(f"Processing file: {path}")

    with open(path, 'rb') as img_file:
        img_data = img_file.read()
        
        # Convert image to base64 for Ollama
        img_base64 = base64.b64encode(img_data).decode('utf-8')
        
        # Use the correct approach as per Gemma 3 documentation - images at top level
        response = ollama.generate(
            model='llava:latest',
            format="json",
            prompt="Describe the image as a subject and a collection of keywords. Return the response in JSON format. Use the following schema: { subject: string, keywords: string[] }",
            images=[img_base64]  # Pass base64 encoded image data at top level
        )
        
        if update_exif:
            update_file(path, response['response'], output_path)
        else:
            print(response['response'])


def update_file(file_path, description_json, output_path):
    print(f"Updating file: {file_path}")
    try:
        with open(file_path, "rb") as img_file:
            img = ExifImage(img_file)
            if description_json is not None:
                data = json.loads(description_json)
                description = f"{data['subject']} ({', '.join(data['keywords'])})"
                print(f"Setting description: {description}")
                img.image_description = description

            if output_path is None:
                filename, extension = os.path.splitext(file_path)
                file_path = filename + "_edited" + extension
            else:
                if not os.path.isabs(output_path):
                    output_path = os.path.join(os.path.dirname(file_path), output_path)
                    if not os.path.exists(output_path):
                        os.makedirs(output_path)
                file_path = os.path.join(output_path, os.path.basename(file_path))
            with open(file_path, "wb") as ofile:
                ofile.write(img.get_file())
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")


if __name__ == "__main__":
    output_path = None
    update_exif = False

    if len(sys.argv) > 2:
        operation = sys.argv[1]
        path = sys.argv[2]
        if not os.path.isabs(path):
            path = os.path.abspath(path)

        if operation == "update":
            update_exif = True
            for i in range(3, len(sys.argv)):
                if sys.argv[i].startswith("-output:"):
                    output_path = sys.argv[i+1]
    else:
        print(
            "Usage: python ai-image-dec-exif.py <operation> <path> -output: [output_path]")
        print("operation: 'ask' or 'update'")
        print("path: path to the image file or folder")
        print("output_path: path to write updated files to; if not provided, files would be renamed with '_edited' (optional parameter)")
        sys.exit(1)

    if operation == "ask":
        ask_llm(path)
    elif operation == "update":
        ask_llm(path, update_exif, output_path)
    else:
        print("One or both of the provided paths are not valid directories.")
