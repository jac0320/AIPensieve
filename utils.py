import os
import PIL
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import requests
import streamlit as st
import requests
import os
import json
import pandas as pd
from datetime import datetime, timezone
from geopy.geocoders import GoogleV3
import pytz
import time
from timezonefinder import TimezoneFinder
from constants import OPENWEATHER_API_KEY, GOOGLEV3_API_KEY



def stream_data(response):
    for word in response.split(" "):
        yield word + " "
        time.sleep(0.007)


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


def get_image_metadata(image, exclude_tags=None):
    """ 
        Extracts general EXIF metadata from a JPEG image file if available, excluding specified tags. 
    """
    
    if exclude_tags is None:
        exclude_tags = ['MakerNote']  # Default tags to exclude

    with Image.open(image) as img:
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


def get_historical_weather(lat, lon, date):
    """
    Fetch historical weather data for a specific latitude, longitude, and date.
    
    Args:
    - lat (float): Latitude of the location
    - lon (float): Longitude of the location
    - date (str): Date in 'YYYY-MM-DD' format
    - api_key (str): API key for the OpenWeatherMap API
    
    Returns:
    - DataFrame with weather data or an error message
    """
    # Convert date to UNIX timestamp
    timestamp = int(datetime.strptime(date, '%Y-%m-%d %H:%M:%S').timestamp())
    
    # Build the API URL
    url = f"https://api.openweathermap.org/data/3.0/onecall/timemachine?lat={lat}&lon={lon}&dt={timestamp}&appid={OPENWEATHER_API_KEY}"
    
    # Make the API request
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        # Extract hourly weather data and convert to DataFrame
        df = pd.DataFrame(data)
        return df
    else:
        return f"Failed to fetch data: {response.text}"
    

def convert_to_utc_str(time_str):
    # Parse the datetime string with timezone information
    dt_with_tz = datetime.strptime(time_str, '%Y:%m:%d %H:%M:%S%z')
    
    # Convert to UTC
    dt_utc = dt_with_tz.astimezone(timezone.utc)
    
    # Format the UTC datetime as a string without the timezone offset
    utc_time_str = dt_utc.strftime('%Y-%m-%d %H:%M:%S')
    
    return utc_time_str


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, PIL.TiffImagePlugin.IFDRational):
            # Convert IFDRational to a serializable format, e.g., string or float
            return str(obj)  # or float(obj.numerator) / obj.denominator
        elif isinstance(obj, bytes):
            # Convert bytes to a string format, here using base64 to ensure all byte data is accurately encoded
            import base64
            return base64.b64encode(obj).decode('utf-8')
        elif isinstance(obj, pd.DataFrame):
            return obj.to_json()
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)
    

def locate_address_google_map(address):
    
    geolocator = GoogleV3(api_key=GOOGLEV3_API_KEY)
    location = geolocator.geocode(address)
    if location:
        return location.latitude, location.longitude
    else:
        st.session_state.logger.error("Location could not be geocoded")


def convert_raw_date_to_utc_dt(date_str, latitude, longitude):
    # Parsing the date string
    date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')

    # Finding the timezone based on latitude and longitude
    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lat=latitude, lng=longitude)
    timezone = pytz.timezone(timezone_str)

    # Localize the date to found timezone
    localized_date = timezone.localize(date)

    # Convert to UTC
    utc_date = localized_date.astimezone(pytz.utc)

    # Formatting the UTC datetime string
    utc_date_str = utc_date.strftime('%Y-%m-%d %H:%M:%S')
    return utc_date_str
    
