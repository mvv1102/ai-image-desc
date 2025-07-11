# AI assisted image description tool

A simple python script that embeds description of images into exif metadata based on AI generated subject and keywords. The keywords are generated using [Ollama.ai](https://ollama.ai) platform. 

## Benefits
There are two main benefits of this tool:
1. It runs completely locally on you computer, so no need for sending your photos to the cloud for porcessing, no need to pay LLM useage fees, no need to high bandwidth internet connection.
2. You can use Windows Explorer to search you photos based on those tags! Just type *Subject: \<your search keyword\>* in the Explorer's search box and it will filter the photos down to only ones that match the keyword. How cool is that!

## Usage

You must have [Ollama](https://ollama.ai) installed and you must pull the model(s) you want to use. The script expect model already be pulled. Default model is `gemma3:latest`

Pull the repo to your local drive and install script dependencies from the `requirements.txt` file (exif and ollama).

### Command:
>python ai-image-desc-exif.py \<operation\> \<path\> -output: [output_path] -model: [model]

**operation**: `ask` or `update`

**path**: path to the image file or folder

**output_path**: path to write updated files to; if not provided, files would be renamed with `_edited` suffix (optional parameter)

**model**: LLM to use for the description, default is `gemma3:latest` (optional parameter)

## Notes
While the script does not overwrite the original files, it's good idea to have a backup first. I'm not responsible for any data loss.

This tool is inspired by [AI Renamer project](https://github.com/technovangelist/airenamer)