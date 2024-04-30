import google.generativeai as genai



def random_self_intro():
    prompt = f"""
    Build a random person character and write a few setence of description.
    """
    model = genai.GenerativeModel('gemini-pro')
    return model.generate_content(prompt).text