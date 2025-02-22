from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from models import User
from schemas import UserCreate, Token
from auth import get_password_hash, verify_password, create_access_token
from dependencies import get_current_user
from datetime import timedelta

app = FastAPI()
Base.metadata.create_all(bind=engine)


from fastapi import Response

print("Hello")

@app.get("/", response_model=dict)
def dummy():
    print("Hello")
    return {"msg": "Hello FastAPI"}

print("Hello")
@app.post("/signup", response_model=Token)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    access_token = create_access_token({"sub": db_user.username}, timedelta(minutes=60))
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    access_token = create_access_token({"sub": user.username}, timedelta(minutes=60))
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/token", response_model=Token)
def token_endpoint(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    return login(form_data, db)


@app.get("/test")
def test_route(current_user: str = Depends(get_current_user)):
    return {"message": f"Hello, {current_user}! You are authenticated."}
