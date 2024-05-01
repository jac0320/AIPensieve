import streamlit as st
import os
import google.generativeai as genai
import PIL.Image
import re
import json
from tenacity import retry, wait_random_exponential, stop_after_attempt

from constants import OPENWEATHER_API_KEY, DEFAULT_EMBEDDING_MODEL, DEFAULT_LOCAL_VECTOR_STORE
from utils import *



def generate_journal(
    personal_intro, 
    filestream=None, 
    metadata=None, 
    location_data=None, 
    weather_data=None, 
    mood_data=None,
    user_journal=None,
):

    prompt = f"""{personal_intro}"""

    if mood_data:
        prompt += f"""
        I am feeling {mood_data} today. 
        """
    
    if location_data:
        prompt += f"""
        This was a picture taken at: 
        {location_data}
        """
    
    if metadata:
        prompt += f"""
        Here are some more information about the picture: 
        {metadata}
        """
        
    if weather_data:
        prompt += f"""
        Here are some weather information at the time:
        {weather_data}
        """
    
    if user_journal:
        prompt += f"""
        Here is some writings I have about it:
        {user_journal}
        """

    prompt += """    
    Based on the all above information and the picture provided, can you write a personal journal. 
    Don't mention anything related to technical data provided above.
    Understand what is in the pictutre in the journal. It is okay to keep the imagination open. 
    Be creative, personal, and realistic. 
    """
    
    st.session_state.logger.info(f"Session {st.session_state.session_id} | Journal Writing Prompt: {prompt}")

    if filestream:
        img = PIL.Image.open(filestream)
        vision_model = genai.GenerativeModel('gemini-pro-vision')
        response = vision_model.generate_content([prompt, img])
    else:
        language_model = genai.GenerativeModel('gemini-pro')
        response = language_model.generate_content([prompt])

    return response.text


def write_journal_title(journal):
    prompt = f"""
        Given the journal below:
        {journal}

        Help me generate a title for this journal
    """
    language_model = genai.GenerativeModel('gemini-pro')
    response = language_model.generate_content(prompt)
    st.session_state.logger.info(f"Session {st.session_state.session_id} | Journal Title Generation Prompt: {prompt}")
    return response.text


@retry(wait=wait_random_exponential(multiplier=1, max=2), stop=stop_after_attempt(3))
def find_journal_metadata(journal_writing):

    try:
        
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"""
            Given the journal below:
            {journal_writing}

            Help me extract info into a dictionary in json format with the following keys:
                location_str: str, extracted location of where this journal is written
                datetime: str, extracted time of the journal in the format of %Y-%m-%d %H:%M:%S
                mood_data: str, describe the overall mood of the journal
                weather_data: str, extract any information that implies weather data
        """
        response = model.generate_content(prompt)
        pattern = r"```json(.*?)```"
        match = re.search(pattern, response.text, re.DOTALL)
        metadata = json.loads(match.group(1))

        assert 'location_str' in metadata
        assert 'datetime' in metadata
        assert 'mood_data' in metadata
        assert 'weather_data' in metadata
    except Exception as e:
        st.session_state.logger.error(f"Session {st.session_state.session_id} | Unable to generate metadata from journal_writing due to {e}. Prompt={prompt} Last response={response.text}")
        return {}

    st.session_state.logger.info(f"Session {st.session_state.session_id} | Journal metadat: {metadata}")    
    return metadata



@st.cache_data
def extract(self_intro, media_file, journal_writing):

    entry = {}

    if media_file is not None:  # primary process media file for rich metadatas
        entry['uuid'] = hash(media_file.name + "" if journal_writing is None else journal_writing)
        entry['media_file'] = media_file.name
        entry['metadata'] = get_image_metadata(media_file)
        entry['gps_data'] = get_image_gps_data(media_file)
        entry['latitude'] = dms_to_decimal(*entry['gps_data']['GPSLatitude'], entry['gps_data']['GPSLatitudeRef'])
        entry["longitude"] = dms_to_decimal(*entry['gps_data']['GPSLongitude'], entry['gps_data']['GPSLongitudeRef'])
        entry['location_data'] = get_location_by_coordinates(entry['latitude'], entry["longitude"])
        entry['utc_dt'] = convert_to_utc_str(entry['metadata']['DateTime'] + entry['metadata']['OffsetTime'])
        entry['openweather_response'] = get_historical_weather(entry['latitude'], entry["longitude"], entry['utc_dt'])
        entry['weather_data'] = entry['openweather_response'].data.loc[0]
        entry['timezone'] = entry['openweather_response'].timezone.loc[0]
        entry['user_journal'] = journal_writing
        entry['journal'] = generate_journal(
            self_intro,
            media_file,
            entry.get('metadata'), 
            entry.get('location_data'), 
            entry.get('weather_data'), 
            entry.get('mood_data'),
            entry.get('user_journal')
        )
        entry['journal_title'] = write_journal_title(entry['journal'])
    else:
        entry['uuid'] = hash(journal_writing)
        entry['media_file'] = None
        entry['metadata'] = None
        entry['gps_data'] = None
        entry['user_journal'] = journal_writing
        entry['journal_title'] = write_journal_title(journal_writing)
        journal_metadata = find_journal_metadata(journal_writing)

        if len(journal_metadata) > 0:
            entry['latitude'], entry["longitude"] = locate_address_google_map(journal_metadata['location_str'])
            entry['location_data'] = get_location_by_coordinates(entry['latitude'], entry["longitude"])
            entry['utc_dt'] = convert_raw_date_to_utc_dt(journal_metadata['datetime'], entry['latitude'], entry["longitude"])
            entry['openweather_response'] = get_historical_weather(entry['latitude'], entry["longitude"], entry['utc_dt'])
            entry['weather_data'] = entry['openweather_response'].data.loc[0]
            entry['timezone'] = entry['openweather_response'].timezone.loc[0]
            entry['mood_data'] = journal_metadata.get('mood_data')
        else:
            entry['latitude'], entry["longitude"] = None, None
            entry['location_data'] = None
            entry['utc_dt'] = None
            entry['weather_data'] = None
            entry['timezone'] = None
            entry['mood_data'] = None

    
    user = st.session_state['user']
    st.session_state.logger.info(f"Saving journal entry {entry['uuid']} for user {user}")
    if os.path.exists(f"converted_data/{user.lower()}_journal.json"):
        with open(f"converted_data/{user.lower()}_journal.json", "r") as f:
            journals = json.load(f)
        journals[entry['uuid']] = entry
        with open(f"converted_data/{user.lower()}_journal.json", "w") as f:
            json.dump(journals, f, cls=CustomEncoder)
    else:
        st.session_state.logger.info("No journal data found for user. Creating one")
        with open(f"converted_data/{user.lower()}_journal.json", "w") as f:
            json.dump({entry['uuid']: entry}, f, cls=CustomEncoder)

    return entry