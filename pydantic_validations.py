from pydantic import BaseModel, EmailStr

class SignUpRequest(BaseModel):
    fullName: str
    email: EmailStr
    password: str
    confirmPassword: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class AskRequest(BaseModel):
    query: str