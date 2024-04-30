import os

OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
DEFAULT_LOCAL_VECTOR_STORE = 'localvs'
DEFAULT_EMBEDDING_MODEL = 'models/embedding-001'
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
GOOGLEV3_API_KEY = os.getenv('GOOGLEV3_API_KEY')

PREDEFINED_SELF_INTRODUCTION = {
"site": """My name is Site Wang. I work in the tech industry and is a AI enthusiastic. 
I love my life and is very excited about all the technology development in the world. 
We have a Golden Retriever called Tim and a Orange Cat called Gulu.
""",
"long": f"""My name is Long Cheng. I work in the tech industry and is a AI enthusiastic. 
I love my life and is very excited about all the technology development in the world. 
I recently had a beautiful baby boy called Henry.
"""
}


