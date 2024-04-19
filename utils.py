import os
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import requests
import folium


def get_filenames(folderpath):
    filenames = []
    for filename in os.listdir(folderpath):
        if os.path.isfile(os.path.join(folderpath, filename)):
            filenames.append(filename)
    return filenames


def dms_to_decimal(degrees, minutes, seconds, direction):
    """Converts degrees, minutes, and seconds to decimal degrees."""
    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
    if direction in ['S', 'W']:
        decimal = -decimal
    return decimal


def get_image_metadata(image_path, exclude_tags=None):
    """ Extracts general EXIF metadata from a JPEG image file if available, excluding specified tags. """
    if exclude_tags is None:
        exclude_tags = ['MakerNote']  # Default tags to exclude

    with Image.open(image_path) as img:
        exif_data = img._getexif()
        if not exif_data:
            return "No EXIF metadata found"

        # Filter out unwanted tags
        filtered_metadata = {
            TAGS.get(key, key): val for key, val in exif_data.items() if TAGS.get(key, key) not in exclude_tags
        }

        # Optionally, process and include detailed GPS data if available and not excluded
        if 'GPSInfo' in filtered_metadata and 'GPSInfo' not in exclude_tags:
            gps_info = {}
            for key, val in filtered_metadata['GPSInfo'].items():
                decode = GPSTAGS.get(key, key)
                gps_info[decode] = val
            filtered_metadata['GPSInfo'] = gps_info  # Replace GPSInfo code with human-readable form

        return filtered_metadata

def get_image_gps_data(image_path):
    """ Extracts GPS data from a JPEG image file if available. """
    with Image.open(image_path) as img:
        exif_data = img._getexif()
        if not exif_data:
            return "No EXIF metadata found"

        gps_info = {}
        # Check if the GPSInfo tag is present
        gps_tag = {TAGS[key]: val for key, val in exif_data.items() if key in TAGS}
        
        if 'GPSInfo' in gps_tag:
            for key in gps_tag['GPSInfo'].keys():
                decode = GPSTAGS.get(key, key)
                gps_info[decode] = gps_tag['GPSInfo'][key]
            return gps_info
        else:
            return "No GPS data found"

def get_location_by_coordinates(lat, lon):
    """ Returns the location details given latitude and longitude. """
    url = 'https://nominatim.openstreetmap.org/reverse'
    params = {
        'format': 'json',
        'lat': lat,
        'lon': lon,
        'zoom': 18  # Adjust zoom level to your needs
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    return data