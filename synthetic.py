import google.generativeai as genai


def random_self_intro(name=""):
    prompt = f"""
    Build a random person character called {name} and write a few setence of description.
    """
    model = genai.GenerativeModel('gemini-pro')
    return model.generate_content(prompt).text
