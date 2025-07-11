# AI assisted image description tool

A simple python script that embeds description of image files into exif metadata based on AI generated subject and keywords. The keywords are generated using [Ollama.ai](https://ollama.ai). You must have Ollama installed first.

## Benefits


## Usage

>python ai-image-dec-exif.py \<operation\> \<path\> -output: [output_path] -model: [model]

**operation**: `ask` or `update`

**path**: path to the image file or folder

**output_path**: path to write updated files to; if not provided, files would be renamed with `_edited` suffix (optional parameter)

**model**: model to use for the description, default is `gemma3:latest` (optional parameter)

---
While the scrip does not overwrite the original files, it's good idea to have a backup first. I'm not responsible for any data loss.