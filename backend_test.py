
import requests
import sys
import json
import time
from datetime import datetime

class NextObjectiveAPITester:
    def __init__(self, base_url="https://c1629179-3070-4d44-b174-905da5ce2b9f.preview.emergentagent.com"):
        self.base_url = base_url
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.resume_analysis_id = None
        self.selected_career_path = None
        self.custom_career_path = "Space Engineer"  # For testing custom career path selection
        self.standard_analysis = None  # Store standard analysis for comparison
        self.enhanced_analysis = None  # Store enhanced analysis for comparison

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, form_data=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Accept': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, data=form_data)
                elif form_data:
                    response = requests.post(url, data=form_data)
                else:
                    headers['Content-Type'] = 'application/json'
                    response = requests.post(url, json=data, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"Response: {response.text}")
                    return False, response.json()
                except:
                    return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_api_health(self):
        """Test API health endpoint"""
        success, response = self.run_test(
            "API Health Check",
            "GET",
            "",
            200
        )
        if success:
            # Check if the API message has been updated to NextObjective
            if 'message' in response and 'Career Transition API is running' in response['message']:
                print("⚠️ API health message still references 'Career Transition API' instead of 'NextObjective API'")
            return True
        return False

    def test_create_user(self):
        """Test user creation"""
        success, response = self.run_test(
            "Create User",
            "POST",
            "users",
            200,
            data={"email": f"test_user_{datetime.now().strftime('%H%M%S')}@example.com"}
        )
        if success and 'id' in response:
            self.user_id = response['id']
            print(f"Created user with ID: {self.user_id}")
            return True
        return False

    def test_get_career_paths(self):
        """Test getting career paths"""
        success, response = self.run_test(
            "Get Career Paths",
            "GET",
            "career-paths",
            200
        )
        if success and 'career_paths' in response:
            print(f"Retrieved {len(response['career_paths'])} career paths")
            return True
        return False

    def test_upload_resume(self):
        """Test resume upload and analysis"""
        # Create a more detailed test resume for software engineer
        resume_content = """
        John Doe
        Software Engineer with 5+ years of experience
        
        SKILLS
        - Programming: Python, JavaScript, React, Node.js, Java
        - Cloud: AWS, Azure, Docker, Kubernetes
        - Tools: Git, CI/CD, Jira, Agile methodologies
        - Soft Skills: Team leadership, communication, problem-solving
        
        EXPERIENCE
        Senior Software Engineer, Tech Solutions Inc.
        2020-Present
        - Led development of cloud-based applications using microservices architecture
        - Managed team of 5 developers for product delivery
        - Implemented CI/CD pipelines reducing deployment time by 40%
        
        Software Developer, Innovative Systems
        2018-2020
        - Developed web applications using React and Node.js
        - Collaborated with UX designers to implement responsive interfaces
        - Optimized database queries improving application performance
        
        EDUCATION
        Bachelor of Science in Computer Science
        University of Technology, 2018
        """
        
        # Save resume to a file
        with open('/app/test_resume.txt', 'w') as f:
            f.write(resume_content)
        
        # Upload the resume
        with open('/app/test_resume.txt', 'rb') as f:
            files = {'file': ('test_resume.txt', f, 'text/plain')}
            form_data = {'user_id': self.user_id}
            
            success, response = self.run_test(
                "Upload Resume",
                "POST",
                "upload-resume",
                200,
                files=files,
                form_data=form_data
            )
            
            if success and 'id' in response:
                self.resume_analysis_id = response['id']
                self.resume_analysis = response  # Store the analysis for later comparison
                print(f"Resume analyzed with ID: {self.resume_analysis_id}")
                
                # Check if career suggestions were returned
                if 'career_suggestions' in response:
                    print(f"Received {len(response['career_suggestions'])} career suggestions")
                    for suggestion in response['career_suggestions']:
                        print(f"  - {suggestion['career_path']}: {suggestion['match_score'] * 100:.0f}% match")
                
                # Check if skills were extracted
                if 'extracted_skills' in response:
                    print(f"Extracted skills: {', '.join(response['extracted_skills'])}")
                
                return True
            return False

    def test_select_career_path(self):
        """Test career path selection"""
        self.selected_career_path = "Software Engineer"  # Using a default career path
        
        success, response = self.run_test(
            "Select Career Path",
            "POST",
            "select-career-path",
            200,
            data={
                "user_id": self.user_id,
                "selected_career_path": self.selected_career_path
            }
        )
        return success
        
    def test_select_custom_career_path(self):
        """Test custom career path selection (not in master list)"""
        success, response = self.run_test(
            "Select Custom Career Path",
            "POST",
            "select-career-path",
            200,
            data={
                "user_id": self.user_id,
                "selected_career_path": self.custom_career_path
            }
        )
        
        if success:
            print(f"Successfully selected custom career path: {self.custom_career_path}")
            # Store the custom path for later tests
            self.selected_career_path = self.custom_career_path
            return True
        return False

    def test_calculate_career_score(self):
        """Test career score calculation"""
        form_data = {
            'user_id': self.user_id,
            'career_path': self.selected_career_path
        }
        
        success, response = self.run_test(
            "Calculate Career Score",
            "POST",
            "calculate-career-score",
            200,
            form_data=form_data
        )
        
        if success:
            print(f"Career score: {response.get('current_score', 'N/A')}/100")
            if 'skill_gaps' in response:
                print(f"Skill gaps: {', '.join(response['skill_gaps'])}")
            if 'strength_areas' in response:
                print(f"Strengths: {', '.join(response['strength_areas'])}")
            if 'recommendations' in response:
                print(f"Recommendations: {', '.join(response['recommendations'])}")
            return True
        return False
        
    def test_low_match_career_score(self):
        """Test career score calculation for a likely low-match career"""
        # Use a career path that's likely to have a low match with the test resume
        low_match_career = "Graphic Designer"
        
        form_data = {
            'user_id': self.user_id,
            'career_path': low_match_career
        }
        
        success, response = self.run_test(
            "Calculate Low Match Career Score",
            "POST",
            "calculate-career-score",
            200,
            form_data=form_data
        )
        
        if success:
            score = response.get('current_score', 0)
            print(f"Low match career score: {score}/100")
            
            # Check if score is indeed low (below 60)
            if score < 60:
                print("✅ Confirmed low match score (below 60)")
            else:
                print(f"⚠️ Expected low score but got {score}")
                
            return True
        return False

    def test_add_progress_log(self):
        """Test adding a progress log"""
        success, response = self.run_test(
            "Add Progress Log",
            "POST",
            "progress-log",
            200,
            data={
                "user_id": self.user_id,
                "career_path": self.selected_career_path,
                "log_entry": "Completed an online course on advanced programming",
                "activities_completed": ["Finished Python course", "Built a small project"],
                "skills_improved": ["Python", "Problem Solving"]
            }
        )
        return success

    def test_get_user_progress(self):
        """Test getting user progress"""
        success, response = self.run_test(
            "Get User Progress",
            "GET",
            f"user-progress/{self.user_id}",
            200
        )
        
        if success:
            if 'career_score' in response and response['career_score']:
                print(f"Updated career score: {response['career_score'].get('current_score', 'N/A')}/100")
            
            if 'recent_logs' in response:
                print(f"Retrieved {len(response['recent_logs'])} progress logs")
            
            return True
        return False
        
    def test_get_survey_questions(self):
        """Test getting survey questions"""
        success, response = self.run_test(
            "Get Survey Questions",
            "GET",
            "survey-questions",
            200
        )
        
        if success and 'questions' in response:
            print(f"Retrieved {len(response['questions'])} survey questions")
            return True
        return False
        
    def test_submit_survey(self):
        """Test submitting survey responses"""
        # Create mock survey responses
        survey_responses = {
            "1": "Remote",
            "2": 4,  # High work-life balance importance
            "3": "Small (51-200)",
            "4": 3,  # Neutral public speaking comfort
            "5": "Mix of both",
            "6": "Creative expression",
            "7": 3,  # Moderate job security importance
            "8": "Technology",
            "9": 2,  # Slightly willing to relocate
            "10": "1 year"
        }
        
        success, response = self.run_test(
            "Submit Survey",
            "POST",
            "submit-survey",
            200,
            data={
                "user_id": self.user_id,
                "responses": survey_responses
            }
        )
        
        if success:
            print(f"Successfully submitted survey with {len(survey_responses)} responses")
            # Store the survey responses for later comparison
            self.survey_responses = survey_responses
        
        return success
        
    def test_get_enhanced_career_suggestions(self):
        """Test getting enhanced career suggestions based on survey responses"""
        # First, store the standard analysis for comparison
        self.standard_analysis = self.resume_analysis
        
        # Now get enhanced suggestions
        form_data = {'user_id': self.user_id}
        
        success, response = self.run_test(
            "Get Enhanced Career Suggestions",
            "POST",
            "enhanced-career-suggestions",
            200,
            form_data=form_data
        )
        
        if success:
            self.enhanced_analysis = response
            
            # Check if preference_match field exists in career suggestions
            has_preference_match = all('preference_match' in suggestion for suggestion in response.get('career_suggestions', []))
            
            if has_preference_match:
                print("✅ Enhanced suggestions include preference matching information")
                
                # Compare standard and enhanced suggestions
                if self.standard_analysis:
                    self.compare_suggestions(self.standard_analysis, self.enhanced_analysis)
                
                return True
            else:
                print("❌ Enhanced suggestions missing preference matching information")
                return False
        
        return False
        
    def compare_suggestions(self, standard, enhanced):
        """Compare standard and enhanced career suggestions"""
        if not standard or not enhanced:
            print("⚠️ Cannot compare suggestions: missing data")
            return
            
        std_suggestions = standard.get('career_suggestions', [])
        enh_suggestions = enhanced.get('career_suggestions', [])
        
        print(f"\n📊 Comparing standard ({len(std_suggestions)} suggestions) vs enhanced ({len(enh_suggestions)} suggestions):")
        
        # Check if the order of suggestions has changed
        std_paths = [s['career_path'] for s in std_suggestions]
        enh_paths = [s['career_path'] for s in enh_suggestions]
        
        order_changed = std_paths != enh_paths
        if order_changed:
            print("✅ Career suggestion order has changed based on preferences")
        else:
            print("⚠️ Career suggestion order remained the same despite preferences")
        
        # Check if scores have been adjusted
        score_changes = []
        for std in std_suggestions:
            for enh in enh_suggestions:
                if std['career_path'] == enh['career_path']:
                    score_diff = (enh['match_score'] - std['match_score']) * 100
                    score_changes.append((std['career_path'], score_diff))
        
        if score_changes:
            print("\nScore adjustments based on preferences:")
            for path, diff in score_changes:
                direction = "increased" if diff > 0 else "decreased"
                print(f"  - {path}: {abs(diff):.1f}% {direction}")
                
        # Check for preference match explanations
        print("\nPreference match explanations:")
        for suggestion in enh_suggestions[:3]:  # Show top 3 for brevity
            print(f"  - {suggestion['career_path']}: {suggestion.get('preference_match', 'No preference info')}")
        
    def test_get_job_listings(self):
        """Test getting job listings"""
        success, response = self.run_test(
            "Get Job Listings",
            "GET",
            f"mock-jobs/{self.selected_career_path}",
            200
        )
        
        if success and 'jobs' in response:
            print(f"Retrieved {len(response['jobs'])} job listings")
            return True
        return False

def main():
    # Setup
    tester = NextObjectiveAPITester()
    
    # Run tests
    print("\n===== TESTING NEXTOBJECTIVE API WITH SURVEY INTEGRATION =====\n")
    
    # Test API health
    if not tester.test_api_health():
        print("❌ API health check failed, stopping tests")
        return 1
    
    # Test user creation
    if not tester.test_create_user():
        print("❌ User creation failed, stopping tests")
        return 1
    
    # Test getting career paths
    if not tester.test_get_career_paths():
        print("❌ Getting career paths failed")
    
    # Test resume upload and analysis
    if not tester.test_upload_resume():
        print("❌ Resume upload failed")
        return 1
    
    # Test getting survey questions
    if not tester.test_get_survey_questions():
        print("❌ Getting survey questions failed")
    
    # Test submitting survey
    if not tester.test_submit_survey():
        print("❌ Submitting survey failed")
    
    # Test enhanced career suggestions
    if not tester.test_get_enhanced_career_suggestions():
        print("❌ Getting enhanced career suggestions failed")
    
    # Test career path selection
    if not tester.test_select_career_path():
        print("❌ Career path selection failed")
    
    # Test career score calculation
    if not tester.test_calculate_career_score():
        print("❌ Career score calculation failed")
    
    # Test adding progress log
    if not tester.test_add_progress_log():
        print("❌ Adding progress log failed")
    
    # Test getting user progress
    if not tester.test_get_user_progress():
        print("❌ Getting user progress failed")
    
    # Test getting job listings
    if not tester.test_get_job_listings():
        print("❌ Getting job listings failed")
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    
    # Summary of survey integration testing
    print("\n===== SURVEY INTEGRATION TESTING SUMMARY =====")
    if tester.enhanced_analysis:
        print("✅ Enhanced career suggestions endpoint is working")
        if tester.standard_analysis and tester.enhanced_analysis:
            std_count = len(tester.standard_analysis.get('career_suggestions', []))
            enh_count = len(tester.enhanced_analysis.get('career_suggestions', []))
            print(f"✅ Standard analysis: {std_count} suggestions")
            print(f"✅ Enhanced analysis: {enh_count} suggestions")
            
            # Check if all enhanced suggestions have preference_match field
            has_pref = all('preference_match' in s for s in tester.enhanced_analysis.get('career_suggestions', []))
            print(f"{'✅' if has_pref else '❌'} Preference matching information is {'present' if has_pref else 'missing'}")
    else:
        print("❌ Enhanced career suggestions testing failed")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
