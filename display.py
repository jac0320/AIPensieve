import streamlit as st
import pandas as pd

from utils import stream_data


def display_entry(entry: dict, show_media=False, show_full=False):

    st.session_state.logger.info(f"Session {st.session_state.session_id} | Displaying Journal Entry {entry.get('uuid')}")

    if 'user_journal' in entry and entry['user_journal'] is not None:
        with st.chat_message(entry.get('user_journal', 'user'), avatar='📝'):
            st.write_stream(stream_data(f"For this memory you wrote: {entry['user_journal']}"))
    
    if 'journal' in entry:
        with st.chat_message(entry['journal'], avatar='🧙‍♂️'):
            st.write_stream(stream_data(f"You memory: {entry['journal']}"))

    if 'media_file' in entry and show_media:
        st.image(f'media/{entry["media_file"]}', use_column_width=True)

    if 'mood_data' in entry and show_full:
        with st.expander("Moment Mood"):
            st.write(entry.get('mood_data', {}))

    if 'weather_data' in entry and show_full:
        with st.expander("Moment Weather"):
            st.write(entry.get('weather_data', {}))

    if 'location_data' in entry and show_full:
        with st.expander("Moment Location"):
            st.write(entry.get('location_data', {}))
            st.map(
                data=pd.DataFrame(pd.Series({'lat': float(entry['latitude']), 'lon': float(entry['longitude'])})).T, 
                color='#0044ff',
                use_container_width=True,
                zoom=10
            )
    if 'metadata' in entry and show_full:
        with st.expander("Moment Metadata"):
            st.write(entry.get('metadata_data', {}))