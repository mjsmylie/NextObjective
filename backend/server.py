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
import re
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
    preference_match: Optional[str] = "Good alignment with preferences"

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
        print(f"Starting AI analysis for resume: {resume_text[:100]}...")
        
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
                }},
                {{
                    "career_path": "Another Career Title", 
                    "match_score": 0.78,
                    "reasoning": "Another explanation",
                    "key_skills": ["skill1", "skill2", "skill3"]
                }},
                {{
                    "career_path": "Third Career Title",
                    "match_score": 0.72,
                    "reasoning": "Third explanation", 
                    "key_skills": ["skill1", "skill2", "skill3"]
                }}
            ],
            "extracted_skills": ["skill1", "skill2", "skill3", "skill4"],
            "experience_level": "Entry Level/Mid Level/Senior Level"
        }}

        IMPORTANT: Provide exactly 3 career suggestions ranked by match score (0.0-1.0). Consider the person's background, skills, and experience. Return ONLY valid JSON.
        """

        user_message = UserMessage(text=prompt)
        print("Sending message to Claude API...")
        response = await chat.send_message(user_message)
        print(f"Received response from Claude: {str(response)[:200]}...")
        
        # Parse the AI response
        import json
        response_text = str(response)
        print(f"Full response text: {response_text}")
        
        # Find JSON in the response
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx != -1 and end_idx != 0:
            json_str = response_text[start_idx:end_idx]
            print(f"Extracted JSON: {json_str}")
            result = json.loads(json_str)
            print(f"Parsed result: {result}")
            return result
        else:
            print("Could not find JSON in response")
            raise ValueError("No JSON found in response")
        
    except Exception as e:
        print(f"AI analysis error: {e}")
        # Intelligent fallback based on resume content
        return generate_intelligent_fallback(resume_text)

def generate_intelligent_fallback(resume_text: str) -> Dict[str, Any]:
    """Generate intelligent career suggestions based on resume content analysis"""
    resume_lower = resume_text.lower()
    
    # Analyze resume content for keywords
    tech_keywords = ["software", "developer", "programming", "python", "javascript", "react", "coding", "technical", "engineer", "development"]
    business_keywords = ["management", "business", "analyst", "strategy", "operations", "project", "marketing", "sales"]
    creative_keywords = ["design", "creative", "marketing", "content", "writing", "visual", "graphic", "ux", "ui"]
    data_keywords = ["data", "analytics", "analysis", "statistics", "research", "science", "machine learning", "ai"]
    leadership_keywords = ["lead", "manager", "director", "team", "leadership", "supervisor", "coordinator"]
    
    # Count keyword matches
    tech_score = sum(1 for keyword in tech_keywords if keyword in resume_lower)
    business_score = sum(1 for keyword in business_keywords if keyword in resume_lower)
    creative_score = sum(1 for keyword in creative_keywords if keyword in resume_lower)
    data_score = sum(1 for keyword in data_keywords if keyword in resume_lower)
    leadership_score = sum(1 for keyword in leadership_keywords if keyword in resume_lower)
    
    # Determine experience level
    years_match = re.search(r'(\d+)\s*(?:years?|yrs?)', resume_lower)
    if years_match:
        years = int(years_match.group(1))
        if years < 2:
            experience_level = "Entry Level"
        elif years < 5:
            experience_level = "Mid Level"
        else:
            experience_level = "Senior Level"
    else:
        experience_level = "Mid Level"
    
    # Generate suggestions based on keyword analysis
    suggestions = []
    
    # Tech-focused suggestions
    if tech_score >= 3:
        suggestions.append({
            "career_path": "Software Engineer" if experience_level != "Entry Level" else "Junior Software Developer",
            "match_score": 0.85 + (tech_score * 0.02),
            "reasoning": f"Strong technical background with {tech_score} relevant technical skills mentioned",
            "key_skills": ["Programming", "Problem Solving", "Technical Skills"]
        })
        
    # Data-focused suggestions  
    if data_score >= 2 or tech_score >= 2:
        suggestions.append({
            "career_path": "Data Analyst" if experience_level != "Senior Level" else "Senior Data Scientist",
            "match_score": 0.78 + (data_score * 0.03),
            "reasoning": f"Analytical capabilities with {data_score + tech_score} relevant technical and analytical skills",
            "key_skills": ["Data Analysis", "Problem Solving", "Technical Skills"]
        })
    
    # Business/Management suggestions
    if business_score >= 2 or leadership_score >= 2:
        suggestions.append({
            "career_path": "Business Analyst" if experience_level != "Senior Level" else "Product Manager",
            "match_score": 0.75 + (business_score * 0.02),
            "reasoning": f"Business acumen with {business_score + leadership_score} relevant business and leadership skills",
            "key_skills": ["Analysis", "Communication", "Business Strategy"]
        })
    
    # Creative suggestions
    if creative_score >= 2:
        suggestions.append({
            "career_path": "UX Designer" if tech_score > 0 else "Marketing Coordinator",
            "match_score": 0.72 + (creative_score * 0.03),
            "reasoning": f"Creative skills with {creative_score} relevant creative and design skills",
            "key_skills": ["Design", "Creativity", "Communication"]
        })
    
    # Leadership suggestions
    if leadership_score >= 3 and experience_level == "Senior Level":
        suggestions.append({
            "career_path": "Project Manager",
            "match_score": 0.80 + (leadership_score * 0.02),
            "reasoning": f"Strong leadership background with {leadership_score} relevant management skills",
            "key_skills": ["Leadership", "Project Management", "Communication"]
        })
    
    # Ensure we have at least 3 suggestions
    default_suggestions = [
        {
            "career_path": "Business Development Representative",
            "match_score": 0.68,
            "reasoning": "Versatile professional skills suitable for business development",
            "key_skills": ["Communication", "Sales", "Relationship Building"]
        },
        {
            "career_path": "Operations Coordinator", 
            "match_score": 0.65,
            "reasoning": "Organizational skills suitable for operations management",
            "key_skills": ["Organization", "Process Improvement", "Communication"]
        },
        {
            "career_path": "Customer Success Manager",
            "match_score": 0.62,
            "reasoning": "People skills and problem-solving abilities for customer success",
            "key_skills": ["Customer Service", "Problem Solving", "Communication"]
        }
    ]
    
    # Add default suggestions if needed
    while len(suggestions) < 3:
        suggestions.append(default_suggestions[len(suggestions)])
    
    # Sort by match score and take top 3
    suggestions.sort(key=lambda x: x["match_score"], reverse=True)
    suggestions = suggestions[:3]
    
    # Extract skills from resume
    all_skills = ["Communication", "Problem Solving", "Leadership"]
    if tech_score > 0:
        all_skills.extend(["Technical Skills", "Programming"])
    if business_score > 0:
        all_skills.extend(["Business Analysis", "Strategy"])
    if creative_score > 0:
        all_skills.extend(["Design", "Creativity"])
    if data_score > 0:
        all_skills.extend(["Data Analysis", "Research"])
    
    return {
        "career_suggestions": suggestions,
        "extracted_skills": list(set(all_skills))[:6],  # Limit to 6 unique skills
        "experience_level": experience_level
    }

# Enhanced AI function that considers survey responses
async def analyze_resume_with_survey(resume_text: str, survey_responses: Dict[str, Any]) -> Dict[str, Any]:
    try:
        print(f"Starting enhanced AI analysis with survey data...")
        
        chat = LlmChat(
            api_key=ANTHROPIC_API_KEY,
            session_id=str(uuid.uuid4()),
            system_message="You are an expert career counselor who provides personalized career recommendations based on both professional background and personal preferences."
        ).with_model("anthropic", "claude-3-5-sonnet-20241022")

        # Convert survey responses to readable preferences
        preferences_text = format_survey_preferences(survey_responses)

        prompt = f"""
        Analyze this resume and provide personalized career suggestions based on both the professional background and personal preferences:

        RESUME:
        {resume_text}

        PERSONAL PREFERENCES:
        {preferences_text}

        Please provide your analysis in the following JSON format:
        {{
            "career_suggestions": [
                {{
                    "career_path": "Career Title",
                    "match_score": 0.85,
                    "reasoning": "Explanation combining skills match AND preference alignment",
                    "key_skills": ["skill1", "skill2", "skill3"],
                    "preference_match": "How this career aligns with their stated preferences"
                }},
                {{
                    "career_path": "Another Career Title",
                    "match_score": 0.78,
                    "reasoning": "Another explanation with preference consideration",
                    "key_skills": ["skill1", "skill2", "skill3"],
                    "preference_match": "How this career aligns with preferences"
                }},
                {{
                    "career_path": "Third Career Title",
                    "match_score": 0.72,
                    "reasoning": "Third explanation with preference consideration",
                    "key_skills": ["skill1", "skill2", "skill3"],
                    "preference_match": "How this career aligns with preferences"
                }}
            ],
            "extracted_skills": ["skill1", "skill2", "skill3", "skill4"],
            "experience_level": "Entry Level/Mid Level/Senior Level"
        }}

        IMPORTANT: 
        - Provide exactly 3 career suggestions that balance skills AND preferences
        - Rank based on BOTH technical fit AND preference alignment
        - Consider work environment, work-life balance, company size, industry preferences
        - Explain how each suggestion matches their personal preferences
        - Adjust match scores based on preference alignment (boost scores for good preference fits)
        - Return ONLY valid JSON
        """

        user_message = UserMessage(text=prompt)
        print("Sending enhanced message to Claude API...")
        response = await chat.send_message(user_message)
        print(f"Received enhanced response from Claude: {str(response)[:200]}...")
        
        # Parse AI response
        import json
        response_text = str(response)
        print(f"Full enhanced response: {response_text}")
        
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx != -1 and end_idx != 0:
            json_str = response_text[start_idx:end_idx]
            print(f"Extracted enhanced JSON: {json_str}")
            result = json.loads(json_str)
            
            # Ensure preference_match is included in each suggestion
            for suggestion in result.get("career_suggestions", []):
                if "preference_match" not in suggestion:
                    suggestion["preference_match"] = "Good alignment with stated preferences"
            
            print(f"Parsed enhanced result: {result}")
            return result
        else:
            print("Could not find JSON in enhanced response")
            raise ValueError("No JSON found in enhanced response")
            
    except Exception as e:
        print(f"Enhanced AI analysis error: {e}")
        # Return enhanced fallback with actual preference consideration
        return generate_survey_enhanced_fallback(resume_text, survey_responses)

def generate_survey_enhanced_fallback(resume_text: str, survey_responses: Dict[str, Any]) -> Dict[str, Any]:
    """Generate career suggestions that combine resume analysis (70-80%) with survey preferences (20-30%)"""
    
    # Start with intelligent resume analysis (primary factor)
    base_analysis = generate_intelligent_fallback(resume_text)
    
    # Apply survey preference adjustments (secondary factor)
    enhanced_suggestions = []
    
    for suggestion in base_analysis["career_suggestions"]:
        # Calculate preference alignment score (0.0 to 1.0)
        preference_score = calculate_preference_alignment(suggestion["career_path"], survey_responses)
        
        # Apply 20-30% weight to preferences (0.2-0.3 multiplier)
        base_score = suggestion["match_score"]
        preference_adjustment = (preference_score - 0.5) * 0.25  # Max ±12.5% adjustment
        
        # Calculate final score (70-80% resume, 20-30% preferences)
        final_score = min(1.0, max(0.0, base_score + preference_adjustment))
        
        # Generate preference-aware reasoning and explanation
        preference_explanation = generate_preference_explanation(suggestion["career_path"], survey_responses, preference_score)
        
        enhanced_suggestion = {
            "career_path": suggestion["career_path"],
            "match_score": final_score,
            "reasoning": suggestion["reasoning"] + f" Additionally, {preference_explanation['reasoning_addition']}",
            "key_skills": suggestion["key_skills"],
            "preference_match": preference_explanation["preference_match"]
        }
        
        enhanced_suggestions.append(enhanced_suggestion)
    
    # Re-sort by final scores and ensure top 3
    enhanced_suggestions.sort(key=lambda x: x["match_score"], reverse=True)
    
    # Consider swapping in preference-aligned careers if they're much better matches
    alternative_careers = get_preference_aligned_careers(survey_responses)
    for alt_career in alternative_careers:
        alt_score = calculate_preference_alignment(alt_career, survey_responses)
        if alt_score > 0.8:  # High preference alignment
            # Only replace if not already in top suggestions
            existing_careers = [s["career_path"] for s in enhanced_suggestions]
            if alt_career not in existing_careers:
                # Replace lowest scoring suggestion if preference alignment is significantly better
                if len(enhanced_suggestions) >= 3 and alt_score > enhanced_suggestions[2]["match_score"] + 0.1:
                    enhanced_suggestions[2] = {
                        "career_path": alt_career,
                        "match_score": 0.65 + (alt_score * 0.2),  # Base + preference boost
                        "reasoning": f"Good foundational skills with strong alignment to your preferences",
                        "key_skills": get_career_skills(alt_career),
                        "preference_match": generate_preference_explanation(alt_career, survey_responses, alt_score)["preference_match"]
                    }
    
    return {
        "career_suggestions": enhanced_suggestions[:3],
        "extracted_skills": base_analysis["extracted_skills"],
        "experience_level": base_analysis["experience_level"]
    }

def calculate_preference_alignment(career_path: str, survey_responses: Dict[str, Any]) -> float:
    """Calculate how well a career aligns with survey preferences (0.0 to 1.0)"""
    alignment_score = 0.5  # Neutral starting point
    total_factors = 0
    
    career_lower = career_path.lower()
    
    # Work Environment Preference (Question 1)
    if "1" in survey_responses:
        work_env = survey_responses["1"]
        if work_env == "Remote" and any(word in career_lower for word in ["remote", "developer", "writer", "analyst"]):
            alignment_score += 0.15
        elif work_env == "Office" and any(word in career_lower for word in ["manager", "sales", "coordinator"]):
            alignment_score += 0.1
        elif work_env == "Hybrid" and any(word in career_lower for word in ["consultant", "project", "business"]):
            alignment_score += 0.1
        total_factors += 1
    
    # Company Size Preference (Question 3)
    if "3" in survey_responses:
        company_size = survey_responses["3"]
        if "Startup" in company_size and any(word in career_lower for word in ["developer", "designer", "product"]):
            alignment_score += 0.1
        elif "Large" in company_size and any(word in career_lower for word in ["analyst", "specialist", "coordinator"]):
            alignment_score += 0.1
        total_factors += 1
    
    # Career Motivation (Question 6)
    if "6" in survey_responses:
        motivation = survey_responses["6"]
        if motivation == "Creative expression" and any(word in career_lower for word in ["designer", "creative", "content", "marketing"]):
            alignment_score += 0.15
        elif motivation == "Financial growth" and any(word in career_lower for word in ["sales", "business", "manager", "analyst"]):
            alignment_score += 0.1
        elif motivation == "Personal growth" and any(word in career_lower for word in ["consultant", "analyst", "developer"]):
            alignment_score += 0.1
        total_factors += 1
    
    # Industry Interest (Question 8)
    if "8" in survey_responses:
        industry = survey_responses["8"]
        if industry == "Technology" and any(word in career_lower for word in ["developer", "engineer", "analyst", "data"]):
            alignment_score += 0.15
        elif industry == "Healthcare" and any(word in career_lower for word in ["analyst", "coordinator", "researcher"]):
            alignment_score += 0.1
        elif industry == "Marketing" and any(word in career_lower for word in ["marketing", "content", "social", "creative"]):
            alignment_score += 0.15
        total_factors += 1
    
    # Work Style Preference (Question 5)
    if "5" in survey_responses:
        work_style = survey_responses["5"]
        if work_style == "Independently" and any(word in career_lower for word in ["developer", "analyst", "writer", "researcher"]):
            alignment_score += 0.1
        elif work_style == "In teams" and any(word in career_lower for word in ["manager", "coordinator", "consultant"]):
            alignment_score += 0.1
        total_factors += 1
    
    # Ensure score stays within bounds
    return min(1.0, max(0.0, alignment_score))

def generate_preference_explanation(career_path: str, survey_responses: Dict[str, Any], preference_score: float) -> Dict[str, str]:
    """Generate explanations for how the career aligns with preferences"""
    
    explanations = []
    career_lower = career_path.lower()
    
    # Check specific preference alignments
    if "1" in survey_responses and survey_responses["1"] == "Remote":
        if any(word in career_lower for word in ["remote", "developer", "analyst"]):
            explanations.append("supports remote work flexibility")
    
    if "3" in survey_responses:
        company_size = survey_responses["3"]
        if "Small" in company_size:
            explanations.append("fits well in small, agile company environments")
        elif "Large" in company_size:
            explanations.append("suitable for large corporate structures")
    
    if "6" in survey_responses:
        motivation = survey_responses["6"]
        if motivation == "Creative expression" and any(word in career_lower for word in ["designer", "creative", "marketing"]):
            explanations.append("offers creative fulfillment and self-expression")
        elif motivation == "Financial growth":
            explanations.append("provides strong earning potential and career advancement")
    
    if "8" in survey_responses:
        industry = survey_responses["8"]
        if industry == "Technology" and any(word in career_lower for word in ["developer", "engineer", "data"]):
            explanations.append("aligns with your technology industry interest")
    
    # Generate final explanation
    if preference_score > 0.7:
        preference_match = f"Excellent fit: {', '.join(explanations[:3])}" if explanations else "Strong alignment with your stated preferences"
    elif preference_score > 0.5:
        preference_match = f"Good fit: {', '.join(explanations[:2])}" if explanations else "Reasonable alignment with your preferences"
    else:
        preference_match = "Moderate fit based on skills, though some preferences may not align perfectly"
    
    reasoning_addition = "this role aligns well with your survey preferences" if preference_score > 0.6 else "your skills are transferable to this role"
    
    return {
        "preference_match": preference_match,
        "reasoning_addition": reasoning_addition
    }

def get_preference_aligned_careers(survey_responses: Dict[str, Any]) -> List[str]:
    """Get career suggestions specifically aligned with survey preferences"""
    aligned_careers = []
    
    # Remote work preference
    if "1" in survey_responses and survey_responses["1"] == "Remote":
        aligned_careers.extend(["Remote Software Developer", "Digital Marketing Specialist", "Content Writer"])
    
    # Creative motivation
    if "6" in survey_responses and survey_responses["6"] == "Creative expression":
        aligned_careers.extend(["UX Designer", "Graphic Designer", "Content Creator", "Marketing Creative"])
    
    # Technology industry
    if "8" in survey_responses and survey_responses["8"] == "Technology":
        aligned_careers.extend(["Software Engineer", "Product Manager", "Data Analyst"])
    
    # Small company preference
    if "3" in survey_responses and "Small" in survey_responses["3"]:
        aligned_careers.extend(["Startup Product Manager", "Growth Marketing Manager"])
    
    return list(set(aligned_careers))  # Remove duplicates

def get_career_skills(career_path: str) -> List[str]:
    """Get relevant skills for a career path"""
    career_skills = {
        "Remote Software Developer": ["Programming", "Remote Collaboration", "Self-Management"],
        "Digital Marketing Specialist": ["Digital Marketing", "Analytics", "Content Creation"],
        "UX Designer": ["Design", "User Research", "Prototyping"],
        "Content Creator": ["Writing", "Creativity", "Content Strategy"],
        "Product Manager": ["Strategy", "Communication", "Product Development"],
        "Data Analyst": ["Data Analysis", "Statistics", "Problem Solving"]
    }
    
    return career_skills.get(career_path, ["Communication", "Problem Solving", "Adaptability"])

def format_survey_preferences(survey_responses: Dict[str, Any]) -> str:
    """Convert survey responses to readable preference text"""
    preferences = []
    
    # Map question IDs to readable preferences
    question_mapping = {
        1: "Work Environment",
        2: "Work-Life Balance Importance",
        3: "Company Size Preference", 
        4: "Public Speaking Comfort",
        5: "Work Style Preference",
        6: "Career Motivation",
        7: "Job Security Importance",
        8: "Industry Interest",
        9: "Relocation Willingness",
        10: "Career Timeline"
    }
    
    for q_id, response in survey_responses.items():
        if str(q_id) in ["1", "3", "5", "6", "8", "10"]:  # Multiple choice questions
            preferences.append(f"- {question_mapping.get(int(q_id), f'Question {q_id}')}: {response}")
        else:  # Scale questions (2, 4, 7, 9)
            scale_value = int(response) if isinstance(response, (int, str)) else 3
            if int(q_id) == 2:  # Work-life balance
                importance = ["Not important", "Slightly important", "Moderately important", "Very important", "Extremely important"][scale_value-1]
                preferences.append(f"- Work-Life Balance: {importance}")
            elif int(q_id) == 4:  # Public speaking
                comfort = ["Very uncomfortable", "Uncomfortable", "Neutral", "Comfortable", "Very comfortable"][scale_value-1]
                preferences.append(f"- Public Speaking: {comfort}")
            elif int(q_id) == 7:  # Job security
                importance = ["Not important", "Slightly important", "Moderately important", "Very important", "Extremely important"][scale_value-1]
                preferences.append(f"- Job Security: {importance}")
            elif int(q_id) == 9:  # Relocation
                willingness = ["Not willing", "Slightly willing", "Moderately willing", "Very willing", "Extremely willing"][scale_value-1]
                preferences.append(f"- Relocation: {willingness}")
    
    return "\n".join(preferences)

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

@api_router.post("/enhanced-career-suggestions")
async def get_enhanced_career_suggestions(user_id: str = Form(...)):
    """Get career suggestions enhanced with survey responses"""
    # Get user's latest resume analysis
    latest_analysis = await db.resume_analyses.find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)]
    )
    
    if not latest_analysis:
        raise HTTPException(status_code=404, detail="No resume analysis found for user")
    
    # Get user's survey responses
    latest_survey = await db.survey_responses.find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)]
    )
    
    if not latest_survey:
        # No survey data, return original analysis
        return latest_analysis
    
    # Extract resume text from skills and experience level (simplified)
    resume_text = f"Skills: {', '.join(latest_analysis['extracted_skills'])}\nExperience Level: {latest_analysis['experience_level']}"
    
    # Get enhanced suggestions using survey data
    enhanced_analysis = await analyze_resume_with_survey(resume_text, latest_survey['responses'])
    
    # Create enhanced analysis response
    analysis = ResumeAnalysisResponse(
        user_id=user_id,
        career_suggestions=[CareerSuggestion(**suggestion) for suggestion in enhanced_analysis["career_suggestions"]],
        extracted_skills=enhanced_analysis["extracted_skills"],
        experience_level=enhanced_analysis["experience_level"]
    )
    
    # Update original analysis with enhanced suggestions
    await db.resume_analyses.update_one(
        {"id": latest_analysis["id"]},
        {"$set": {"career_suggestions": [s.dict() for s in analysis.career_suggestions]}}
    )
    
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
