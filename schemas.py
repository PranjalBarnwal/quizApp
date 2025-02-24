from pydantic import BaseModel
from typing import List

class UserCreate(BaseModel):
    username: str
    password: str
    is_admin: bool = False  # Default to regular user

class UserLogin(BaseModel):
    username: str
    password: str

class QuizCreate(BaseModel):
    title: str
    total_score: int
    duration: int

class QuestionCreate(BaseModel):
    text: str
    options: List[str]
    correct_option: int  # Index of correct option

class QuizAttemptCreate(BaseModel):
    quiz_id: int
