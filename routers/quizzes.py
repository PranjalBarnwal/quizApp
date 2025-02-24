from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from database import get_db
from models import Quiz, QuizAttempt, Question, QuestionOption
from schemas import QuizCreate, QuestionCreate
from utils import get_current_user, is_admin

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])

@router.post("/")
def create_quiz(quiz_data: QuizCreate, db: Session = Depends(get_db), current_user: dict = Depends(is_admin)):
    quiz = Quiz(title=quiz_data.title, total_score=quiz_data.total_score, duration=quiz_data.duration)
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz

@router.post("/{quiz_id}/questions", status_code=status.HTTP_201_CREATED)
def add_question(quiz_id: int, question_data: QuestionCreate, db: Session = Depends(get_db), current_user: dict = Depends(is_admin)):
    """
    Admin adds a question to a quiz with multiple options.
    """

    # Ensure quiz exists
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Create question
    question = Question(text=question_data.text, quiz_id=quiz_id)
    db.add(question)
    db.commit()
    db.refresh(question)

    # Add question options
    for index, option_text in enumerate(question_data.options):
        is_correct = (index == question_data.correct_option)  # Match correct answer index
        option = QuestionOption(question_id=question.id, option_text=option_text, is_correct=is_correct)
        db.add(option)

    db.commit()
    
    return {"message": "Question added successfully", "question_id": question.id}

@router.post("/{quiz_id}/start")
def start_quiz(quiz_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = current_user["user"].id

    # Check if quiz exists
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Check if the user has already started the quiz
    attempt = db.query(QuizAttempt).filter_by(user_id=user_id, quiz_id=quiz_id).first()
    if attempt:
        raise HTTPException(status_code=400, detail="Quiz already started or attempted")

    # Record quiz start time
    new_attempt = QuizAttempt(user_id=user_id, quiz_id=quiz_id, start_time=datetime.utcnow())
    db.add(new_attempt)
    db.commit()
    
    return {"message": "Quiz started successfully", "quiz_id": quiz_id, "duration": quiz.duration}

@router.post("/{quiz_id}/submit")
def submit_quiz(quiz_id: int, user_answers: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    User submits answers, system calculates the score correctly.
    """

    user_id = current_user["user"].id

    # Ensure quiz attempt exists
    attempt = db.query(QuizAttempt).filter_by(user_id=user_id, quiz_id=quiz_id).first()
    if not attempt:
        raise HTTPException(status_code=400, detail="Quiz not started")

    # Get quiz details
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Check if quiz time has expired
    time_elapsed = datetime.utcnow() - attempt.start_time
    if time_elapsed > timedelta(minutes=quiz.duration):
        raise HTTPException(status_code=400, detail="Quiz time has expired")

    correct_answers = 0
    total_questions = len(user_answers["answers"])
    answer_data = []  # Store answer data for response

    for answer in user_answers["answers"]:
        question_id = answer["question_id"]
        selected_option_id = answer.get("selected_option")  # Ensure no missing data

        # Fetch the correct option
        correct_option = db.query(QuestionOption).filter(
            QuestionOption.question_id == question_id,
            QuestionOption.is_correct == True
        ).first()

        # Fetch the selected option
        selected_option = db.query(QuestionOption).filter(
            QuestionOption.id == selected_option_id
        ).first()

        # Add to answer response
        answer_data.append({
            "question_id": question_id,
            "selected_option": selected_option.id if selected_option else None,
            "correct_option": correct_option.id if correct_option else None
        })

        # Validate and calculate score
        if selected_option and correct_option and selected_option.id == correct_option.id:
            correct_answers += 1  # Increment score for correct answers

    # Calculate correct score
    final_score = (correct_answers / total_questions) * quiz.total_score if total_questions > 0 else 0

    # Update quiz attempt with correct score
    attempt.score = final_score
    db.commit()

    return {"message": "Quiz submitted successfully", "score": final_score, "answers": answer_data}


@router.get("/")
def get_quizzes(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return db.query(Quiz).all()



@router.get("/{quiz_id}/response")
def get_quiz_response(quiz_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Retrieve the quiz result for the logged-in user.
    """

    user_id = current_user["user"].id

    # Check if the quiz exists
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Check if the user has attempted the quiz
    attempt = db.query(QuizAttempt).filter_by(user_id=user_id, quiz_id=quiz_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="No attempt found for this quiz")

    # Fetch user responses
    questions = db.query(Question).filter(Question.quiz_id == quiz_id).all()
    response_data = []

    for question in questions:
        selected_option = db.query(QuestionOption).filter(
            QuestionOption.question_id == question.id,
            QuestionOption.id == attempt.id  # This should be linked to user-selected answers
        ).first()

        correct_option = db.query(QuestionOption).filter(
            QuestionOption.question_id == question.id,
            QuestionOption.is_correct == True
        ).first()

        response_data.append({
            "question_id": question.id,
            "selected_option": selected_option.id if selected_option else None,
            "correct_option": correct_option.id if correct_option else None
        })

    return {
        "quiz_id": quiz_id,
        "total_score": quiz.total_score,
        "user_score": attempt.score,
        "answers": response_data
    }
