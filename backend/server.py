from fastapi import FastAPI, APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import PyPDF2
import io
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Initialize LLM Chat
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Career paths master list
CAREER_PATHS = [
    "Software Engineer", "Data Scientist", "Product Manager", "UX/UI Designer",
    "Digital Marketing Manager", "Business Analyst", "Project Manager", "Sales Manager",
    "Content Writer", "Graphic Designer", "Financial Analyst", "HR Manager",
    "Operations Manager", "Customer Success Manager", "Cybersecurity Analyst",
    "Machine Learning Engineer", "DevOps Engineer", "Marketing Coordinator",
    "Consultant", "Account Manager", "Quality Assurance Engineer", "Systems Administrator",
    "Network Engineer", "Database Administrator", "Mobile App Developer",
    "Web Developer", "Technical Writer", "Social Media Manager", "Event Coordinator",
    "Training Specialist"
]

# Pydantic Models
class ResumeAnalysisRequest(BaseModel):
    resume_text: str

class CareerSuggestion(BaseModel):
    career_path: str
    match_score: float
    reasoning: str
    key_skills: List[str]

class ResumeAnalysisResponse(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    career_suggestions: List[CareerSuggestion]
    extracted_skills: List[str]
    experience_level: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CareerPathSelection(BaseModel):
    user_id: str
    selected_career_path: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class CareerScore(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    career_path: str
    current_score: float
    max_score: float = 100.0
    skill_gaps: List[str]
    strength_areas: List[str]
    recommendations: List[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ProgressLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    career_path: str
    log_entry: str
    activities_completed: List[str]
    skills_improved: List[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SurveyResponse(BaseModel):
    user_id: str
    responses: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class JobListing(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    company: str
    location: str
    description: str
    requirements: List[str]
    salary_range: Optional[str] = None
    url: str
    career_path: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Helper function to extract text from PDF
async def extract_text_from_pdf(file_content: bytes) -> str:
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text.strip()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error extracting text from PDF: {str(e)}")

# AI helper function
async def analyze_resume_with_ai(resume_text: str) -> Dict[str, Any]:
    try:
        chat = LlmChat(
            api_key=ANTHROPIC_API_KEY,
            session_id=str(uuid.uuid4()),
            system_message="You are a career counselor and resume analysis expert. Analyze resumes and provide career suggestions based on skills, experience, and background."
        ).with_model("anthropic", "claude-3-5-sonnet-20241022")

        prompt = f"""
        Analyze this resume and provide career suggestions:

        {resume_text}

        Please provide your analysis in the following JSON format:
        {{
            "career_suggestions": [
                {{
                    "career_path": "Career Title",
                    "match_score": 0.85,
                    "reasoning": "Explanation of why this career fits",
                    "key_skills": ["skill1", "skill2", "skill3"]
                }}
            ],
            "extracted_skills": ["skill1", "skill2", "skill3", "skill4"],
            "experience_level": "Entry Level/Mid Level/Senior Level"
        }}

        Provide 3-5 career suggestions ranked by match score (0.0-1.0). Consider the person's background, skills, and experience.
        """

        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        # Parse the AI response - in a real implementation you'd want more robust parsing
        import json
        try:
            # Extract JSON from the response
            response_text = str(response)
            # Find JSON in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
        except:
            pass
        
        # Fallback response if AI parsing fails
        return {
            "career_suggestions": [
                {
                    "career_path": "Software Engineer",
                    "match_score": 0.8,
                    "reasoning": "Based on technical background and skills",
                    "key_skills": ["Programming", "Problem Solving", "Technical Skills"]
                }
            ],
            "extracted_skills": ["Communication", "Leadership", "Technical Skills"],
            "experience_level": "Mid Level"
        }
    except Exception as e:
        # Fallback for AI errors
        return {
            "career_suggestions": [
                {
                    "career_path": "Business Analyst",
                    "match_score": 0.75,
                    "reasoning": "General business skills and analytical thinking",
                    "key_skills": ["Analysis", "Communication", "Problem Solving"]
                }
            ],
            "extracted_skills": ["Communication", "Analysis", "Problem Solving"],
            "experience_level": "Mid Level"
        }

# Calculate career score using AI
async def calculate_career_score_with_ai(resume_text: str, career_path: str) -> Dict[str, Any]:
    try:
        chat = LlmChat(
            api_key=ANTHROPIC_API_KEY,
            session_id=str(uuid.uuid4()),
            system_message="You are a career assessment expert. Evaluate how well a candidate's resume matches a specific career path."
        ).with_model("anthropic", "claude-3-5-sonnet-20241022")

        prompt = f"""
        Evaluate this resume for the career path: {career_path}

        Resume:
        {resume_text}

        Provide a detailed assessment in JSON format:
        {{
            "current_score": 75,
            "skill_gaps": ["gap1", "gap2", "gap3"],
            "strength_areas": ["strength1", "strength2"],
            "recommendations": [
                "Take online course in X",
                "Gain experience in Y through volunteering",
                "Network with professionals in Z field"
            ]
        }}

        Score should be 0-100 based on how well the resume matches the ideal candidate for {career_path}.
        """

        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        # Parse AI response
        import json
        try:
            response_text = str(response)
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
        except:
            pass
        
        # Fallback
        return {
            "current_score": 70,
            "skill_gaps": ["Industry Knowledge", "Advanced Skills", "Leadership Experience"],
            "strength_areas": ["Communication", "Basic Skills"],
            "recommendations": [
                "Take relevant online courses",
                "Gain hands-on experience through projects",
                "Network with industry professionals"
            ]
        }
    except Exception as e:
        return {
            "current_score": 65,
            "skill_gaps": ["Technical Skills", "Industry Experience"],
            "strength_areas": ["Communication", "Problem Solving"],
            "recommendations": [
                "Complete online courses",
                "Build a portfolio",
                "Join professional communities"
            ]
        }

# Routes

@api_router.post("/users", response_model=User)
async def create_user(email: Optional[str] = None):
    user = User(email=email)
    await db.users.insert_one(user.dict())
    return user

@api_router.post("/upload-resume")
async def upload_resume(
    user_id: str = Form(...),
    file: UploadFile = File(...)
):
    # Validate file type
    if not file.filename.lower().endswith(('.pdf', '.txt')):
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported")
    
    # Read file content
    content = await file.read()
    
    # Extract text based on file type
    if file.filename.lower().endswith('.pdf'):
        resume_text = await extract_text_from_pdf(content)
    else:
        resume_text = content.decode('utf-8')
    
    # Analyze with AI
    analysis_result = await analyze_resume_with_ai(resume_text)
    
    # Create analysis response
    analysis = ResumeAnalysisResponse(
        user_id=user_id,
        career_suggestions=[CareerSuggestion(**suggestion) for suggestion in analysis_result["career_suggestions"]],
        extracted_skills=analysis_result["extracted_skills"],
        experience_level=analysis_result["experience_level"]
    )
    
    # Store in database
    await db.resume_analyses.insert_one(analysis.dict())
    
    return analysis

@api_router.get("/career-paths")
async def get_career_paths():
    return {"career_paths": CAREER_PATHS}

@api_router.post("/select-career-path")
async def select_career_path(selection: CareerPathSelection):
    await db.career_selections.insert_one(selection.dict())
    return {"message": "Career path selected successfully"}

@api_router.post("/calculate-career-score")
async def calculate_career_score(user_id: str = Form(...), career_path: str = Form(...)):
    # Get user's latest resume analysis
    latest_analysis = await db.resume_analyses.find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)]
    )
    
    if not latest_analysis:
        raise HTTPException(status_code=404, detail="No resume analysis found for user")
    
    # Get resume text (for now, we'll use extracted skills as proxy)
    resume_text = f"Skills: {', '.join(latest_analysis['extracted_skills'])}\nExperience Level: {latest_analysis['experience_level']}"
    
    # Calculate score with AI
    score_result = await calculate_career_score_with_ai(resume_text, career_path)
    
    # Create career score
    career_score = CareerScore(
        user_id=user_id,
        career_path=career_path,
        current_score=score_result["current_score"],
        skill_gaps=score_result["skill_gaps"],
        strength_areas=score_result["strength_areas"],
        recommendations=score_result["recommendations"]
    )
    
    # Store in database
    await db.career_scores.insert_one(career_score.dict())
    
    return career_score

@api_router.post("/progress-log")
async def add_progress_log(log: ProgressLog):
    await db.progress_logs.insert_one(log.dict())
    
    # Update career score based on progress
    latest_score = await db.career_scores.find_one(
        {"user_id": log.user_id, "career_path": log.career_path},
        sort=[("timestamp", -1)]
    )
    
    if latest_score:
        # Simple score improvement based on activities
        improvement = len(log.activities_completed) * 2 + len(log.skills_improved) * 3
        new_score = min(100, latest_score["current_score"] + improvement)
        
        # Update the score
        await db.career_scores.update_one(
            {"id": latest_score["id"]},
            {"$set": {"current_score": new_score}}
        )
    
    return {"message": "Progress logged successfully"}

@api_router.get("/user-progress/{user_id}")
async def get_user_progress(user_id: str):
    # Get latest career score
    latest_score = await db.career_scores.find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)]
    )
    
    # Get recent progress logs
    progress_logs = await db.progress_logs.find(
        {"user_id": user_id},
        sort=[("timestamp", -1)],
        limit=10
    ).to_list(10)
    
    # Convert ObjectIds to strings for JSON serialization
    if latest_score and "_id" in latest_score:
        latest_score["_id"] = str(latest_score["_id"])
    
    for log in progress_logs:
        if "_id" in log:
            log["_id"] = str(log["_id"])
    
    return {
        "career_score": latest_score,
        "recent_logs": progress_logs
    }

@api_router.get("/mock-jobs/{career_path:path}")
async def get_mock_jobs(career_path: str):
    """Mock job listings - in real implementation would use LinkedIn API"""
    # Handle URL-encoded career paths
    career_path = career_path.replace("%20", " ")
    mock_jobs = [
        JobListing(
            title=f"Senior {career_path}",
            company="Tech Corp",
            location="San Francisco, CA",
            description=f"Exciting opportunity for an experienced {career_path} to join our team...",
            requirements=["5+ years experience", "Strong communication skills", "Team player"],
            salary_range="$80,000 - $120,000",
            url="https://example.com/job1",
            career_path=career_path
        ),
        JobListing(
            title=f"Junior {career_path}",
            company="Innovation Inc",
            location="New York, NY",
            description=f"Entry-level position for aspiring {career_path}...",
            requirements=["1-2 years experience", "Eagerness to learn", "Bachelor's degree"],
            salary_range="$50,000 - $70,000",
            url="https://example.com/job2",
            career_path=career_path
        ),
        JobListing(
            title=f"{career_path} Manager",
            company="Growth LLC",
            location="Remote",
            description=f"Lead a team of {career_path}s in this management role...",
            requirements=["7+ years experience", "Management experience", "Leadership skills"],
            salary_range="$100,000 - $140,000",
            url="https://example.com/job3",
            career_path=career_path
        )
    ]
    
    return {"jobs": [job.dict() for job in mock_jobs]}

@api_router.get("/survey-questions")
async def get_survey_questions():
    questions = [
        {
            "id": 1,
            "question": "What type of work environment do you prefer?",
            "type": "multiple_choice",
            "options": ["Remote", "Office", "Hybrid", "Flexible"]
        },
        {
            "id": 2,
            "question": "How important is work-life balance to you?",
            "type": "scale",
            "min": 1,
            "max": 5,
            "labels": ["Not important", "Very important"]
        },
        {
            "id": 3,
            "question": "What is your preferred company size?",
            "type": "multiple_choice",
            "options": ["Startup (1-50)", "Small (51-200)", "Medium (201-1000)", "Large (1000+)"]
        },
        {
            "id": 4,
            "question": "How comfortable are you with public speaking?",
            "type": "scale",
            "min": 1,
            "max": 5,
            "labels": ["Very uncomfortable", "Very comfortable"]
        },
        {
            "id": 5,
            "question": "Do you prefer working independently or in teams?",
            "type": "multiple_choice",
            "options": ["Independently", "In teams", "Mix of both"]
        },
        {
            "id": 6,
            "question": "What motivates you most in your career?",
            "type": "multiple_choice",
            "options": ["Financial growth", "Personal growth", "Impact on others", "Creative expression"]
        },
        {
            "id": 7,
            "question": "How important is job security to you?",
            "type": "scale",
            "min": 1,
            "max": 5,
            "labels": ["Not important", "Very important"]
        },
        {
            "id": 8,
            "question": "What industry interests you most?",
            "type": "multiple_choice",
            "options": ["Technology", "Healthcare", "Finance", "Education", "Marketing", "Other"]
        },
        {
            "id": 9,
            "question": "How willing are you to relocate for work?",
            "type": "scale",
            "min": 1,
            "max": 5,
            "labels": ["Not willing", "Very willing"]
        },
        {
            "id": 10,
            "question": "What is your ideal career timeline?",
            "type": "multiple_choice",
            "options": ["Immediate transition", "6 months", "1 year", "2+ years"]
        }
    ]
    return {"questions": questions}

@api_router.post("/submit-survey")
async def submit_survey(survey: SurveyResponse):
    await db.survey_responses.insert_one(survey.dict())
    return {"message": "Survey submitted successfully"}

# Basic health check
@api_router.get("/")
async def root():
    return {"message": "NextObjective API is running"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
