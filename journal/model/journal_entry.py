from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class Media(BaseModel):
    url: str
    type: str  # e.g., 'image' or 'video'
    description: Optional[str] = None

class Journal(BaseModel):
    id: int
    title: str
    content: str
    tags: List[str] = []
    mood: Optional[str] = None
    weather: Optional[str] = None
    pictures: List[Media] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


# Example usage
entry = JournalEntry(
    media="photo.jpg",
    date=datetime.now(),
    weather="sunny",
    writing="Today was a great day!"
)

print(entry)