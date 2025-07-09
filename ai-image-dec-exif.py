import base64
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
    "xp_author",
    "xp_keywords",
    "xp_subject",
    "xp_title",
    "xp_comment",
    # "gps_timestamp",
    # "gps_satellites",
    # "gps_status",
    # "gps_measure_mode",
    # "gps_dop",
    # "gps_speed_ref",
    # "gps_speed",
    # "gps_track_ref",
    # "gps_track",
    # "gps_img_direction_ref",
    # "gps_img_direction",
    # "gps_map_datum",
    # "gps_dest_latitude_ref",
    # "gps_dest_latitude",
    # "gps_dest_longitude_ref",
    # "gps_dest_longitude",
    # "gps_dest_bearing_ref",
    # "gps_dest_bearing",
    # "gps_dest_distance_ref",
    # "gps_dest_distance",
    # "gps_processing_method",
    # "gps_area_information",
    # "gps_datestamp",
    # "gps_differential",
    # "gps_horizontal_positioning_error",
]

def ask_llm(folder):
    if os.path.isfile(folder):
        file = os.path.basename(folder)
        file_path = folder
        ask_llm_file(file_path)
    else:
        images = glob.glob(os.path.join(folder, "*.[jJ][pP][gG]")) + \
            glob.glob(os.path.join(folder, "*.[pP][nN][gG]")) + \
            glob.glob(os.path.join(folder, "*.[tT][iI][fF]")) + \
            glob.glob(os.path.join(folder, "*.[bB][mM][pP]"))
        for file in images:
            file_path = os.path.join(folder, file)
            if os.path.isfile(file_path):
                ask_llm_file(file_path)

def ask_llm_file(path):
    print(f"Processing file: {path}")

    with open(path, 'rb') as img_file:
        img_data = img_file.read()
        
        # Convert image to base64 for Ollama
        img_base64 = base64.b64encode(img_data).decode('utf-8')
        
        # Use the correct approach as per Gemma 3 documentation - images at top level
        response = ollama.generate(
            model='llava:13b',
            format="json",
            prompt="Describe the image as a subject and a collection of keywords. Return the response in JSON format. Use the following schema: { subject: string, keywords: string[] }",
            images=[img_base64]  # Pass base64 encoded image data at top level
        )
        
        print(response['response'])


def readexif_with_exif(folder):
    if os.path.isfile(folder):
        file = os.path.basename(folder)
        file_path = folder
        read_file(file, file_path)
    else:
        images = glob.glob(os.path.join(folder, "*.[jJ][pP][gG]")) + \
            glob.glob(os.path.join(folder, "*.[pP][nN][gG]")) + \
            glob.glob(os.path.join(folder, "*.[tT][iI][fF]")) + \
            glob.glob(os.path.join(folder, "*.[bB][mM][pP]"))
        for file in images:
            file_path = os.path.join(folder, file)
            if os.path.isfile(file_path):
                read_file(file, file_path)


def read_file(file, file_path):
    print(f"Processing file: {file}")
    try:
        with open(file_path, "rb") as img_file:
            img = ExifImage(img_file)

        for tag in EXIF_TAGS:
            value = img.get(tag)
            print("\t{}: {}".format(tag, value))
    except Exception as e:
        print(f"Error reading EXIF data from {file}: {e}")
    print()


def writeexif_with_exif(path, location, altitude, date, artist, output_path):
    if os.path.isfile(path):
        update_file(path, location, altitude, date, artist, output_path)
    elif os.path.isdir(path):
        images = glob.glob(os.path.join(path, "*.[jJ][pP][gG]")) + \
            glob.glob(os.path.join(path, "*.[pP][nN][gG]")) + \
            glob.glob(os.path.join(path, "*.[tT][iI][fF]")) + \
            glob.glob(os.path.join(path, "*.[bB][mM][pP]"))
        for file in images:
            file_path = os.path.join(path, file)
            if os.path.isfile(file_path):
                update_file(file_path, location, altitude, date, artist, output_path)

    print()


def update_file(file_path, location, altitude, date, artist, output_path):
    print(f"Processing file: {file_path}")
    try:
        with open(file_path, "rb") as img_file:
            img = ExifImage(img_file)
            if artist is not None:
                print(f"Setting artist: {artist}")
                img.artist = artist
                img.copyright = f"(c) {artist}, all rights reserved"
                img.image_description = f"Photo by {artist}"

            if date is not None:
                dtstr = date.strftime(DATETIME_STR_FORMAT)
                print(f"Setting datetime: {dtstr}")
                img.datetime = dtstr

            if location is not None:
                print(f"Setting GPS location: {location}")
                img.gps_latitude_ref = "N" if location[0] >= 0 else "S"
                img.gps_longitude_ref = "E" if location[1] >= 0 else "W"
                lat = location[0] if location[0] >= 0 else -location[0]
                lon = location[1] if location[1] >= 0 else -location[1]
                img.gps_latitude = (lat, 0.0, 0.0)
                img.gps_longitude = (lon, 0.0, 0.0)

            if altitude is not None:
                print(f"Setting GPS altitude: {altitude}")
                img.gps_altitude = altitude if altitude >= 0 else -altitude
                img.gps_altitude_ref = 0 if altitude >= 0 else 1  # 0 for above sea level, 1 for below sea level

            if output_path is None:
                filename, extension = os.path.splitext(file_path)
                file_path = filename + "_exif" + extension
            else:
                if not os.path.isabs(output_path):
                    output_path = os.path.join(os.path.dirname(file_path), output_path)
                    if not os.path.exists(output_path):
                        os.makedirs(output_path)
                file_path = os.path.join(output_path, os.path.basename(file_path))
            with open(file_path, "wb") as ofile:
                ofile.write(img.get_file())
            if date is not None:
                os.utime(file_path, (date.timestamp(), date.timestamp()))
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")


if __name__ == "__main__":
    date_format = "%Y-%m-%d"
    lat = None
    lon = None
    altitude = None
    location = None
    date_str = None
    artist = None
    output_path = None
    date_created = None

    if len(sys.argv) > 2:
        operation = sys.argv[1]
        path = sys.argv[2]
        if not os.path.isabs(path):
            path = os.path.abspath(path)

        if operation == "write":
            for i in range(3, len(sys.argv)):
                if sys.argv[i].startswith("-lat:"):
                    lat = float(sys.argv[i+1])
                elif sys.argv[i].startswith("-lon:"):
                    lon = float(sys.argv[i+1])
                elif sys.argv[i].startswith("-alt:"):
                    altitude = float(sys.argv[i+1])
                elif sys.argv[i].startswith("-artist:"):
                    artist = sys.argv[i+1]
                elif sys.argv[i].startswith("-date:"):
                    date_str = sys.argv[i+1]
                elif sys.argv[i].startswith("-output:"):
                    output_path = sys.argv[i+1]
    else:
        print(
            "Usage: python exifedit.py <operation> <path> -date: [date_str] -lat: [latitude] -lon: [longitude] -alt: [altitude] -artist: [artist_name] -output: [output_path]")
        print("operation: 'read' or 'write'")
        print("path: path to the image file or folder")
        print("date_str: date in format YYYY-MM-DD (optional parameter)")
        print("latitude, logitude and altitude: adsolute coordinates, i.e. positive or negative (optional parameters)")
        print("artist_name: string that will get writen into artist and into copyright fields, if desired name contains spaces, surround it with quotes, i.e. \"Name Surname\" (optional parameter)")
        print("output_path: path to write updated files to; if not provided, files would be renamed with '_exif' (optional parameter)")
        sys.exit(1)

    if date_str is not None:
        try:
            date_created = datetime.strptime(date_str, date_format)
        except ValueError:
            print(f"Invalid date format. Expected format: {date_format}")
            sys.exit(1)

    if lat is not None and lon is not None:
        location = (lat, lon)
    else:
        if (lat is None and lon is not None) or (lat is not None and lon is None):
            print("Please provide both latitude and longitude or neither of them.")
            sys.exit(1)

    if operation == "read":
        readexif_with_exif(path)
    elif operation == "write":
        writeexif_with_exif(path, location, altitude, date_created, artist, output_path)
    elif operation == "ask":
        ask_llm(path)
    else:
        print("One or both of the provided paths are not valid directories.")
