from fastapi import FastAPI, Request
from database import engine, Base
from routers import users, quizzes
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse

app = FastAPI()

Base.metadata.create_all(bind=engine)

# Setup rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/second"])
app.state.limiter = limiter


async def custom_rate_limit_handler(request, exc: RateLimitExceeded):
    return JSONResponse(
        {"error": "Rate limit exceeded", "details": str(exc.detail)},
        status_code=429,
    )


app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)
# Add SlowAPI middleware for rate limiting
app.add_middleware(SlowAPIMiddleware)

# 🚀 **Ensure tables are created at startup**
Base.metadata.create_all(bind=engine)

# Include routers
app.include_router(users.router)
app.include_router(quizzes.router)


@app.get("/")
@limiter.limit("10/second")
def home(request: Request):  # ✅ Added request parameter
    return {"message": "Welcome to the Quiz API"}
