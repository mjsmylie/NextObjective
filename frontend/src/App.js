import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || '';

function App() {
  const [currentStep, setCurrentStep] = useState('welcome');
  const [userId, setUserId] = useState('');
  const [resumeAnalysis, setResumeAnalysis] = useState(null);
  const [selectedCareerPath, setSelectedCareerPath] = useState('');
  const [careerScore, setCareerScore] = useState(null);
  const [careerPaths, setCareerPaths] = useState([]);
  const [progressLogs, setProgressLogs] = useState([]);
  const [surveyQuestions, setSurveyQuestions] = useState([]);
  const [surveyResponses, setSurveyResponses] = useState({});
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  
  // Progress tracking state
  const [newLog, setNewLog] = useState('');
  const [activities, setActivities] = useState('');
  const [skills, setSkills] = useState('');
  
  // New state for enhanced features
  const [searchTerm, setSearchTerm] = useState('');
  const [showWarningDialog, setShowWarningDialog] = useState(false);
  const [warningCareerPath, setWarningCareerPath] = useState('');
  const [potentialScore, setPotentialScore] = useState(0);
  const [isEnhancedSuggestions, setIsEnhancedSuggestions] = useState(false);

  useEffect(() => {
    // Create a user session and store user ID
    createUser();
    fetchCareerPaths();
    fetchSurveyQuestions();
  }, []);

  const createUser = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'user@example.com' })
      });
      const userData = await response.json();
      setUserId(userData.id);
      // Store user ID in localStorage for persistence
      localStorage.setItem('nextObjectiveUserId', userData.id);
    } catch (error) {
      console.error('Error creating user:', error);
    }
  };

  const fetchCareerPaths = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/career-paths`);
      const data = await response.json();
      setCareerPaths(data.career_paths);
    } catch (error) {
      console.error('Error fetching career paths:', error);
    }
  };

  const fetchSurveyQuestions = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/survey-questions`);
      const data = await response.json();
      setSurveyQuestions(data.questions);
    } catch (error) {
      console.error('Error fetching survey questions:', error);
    }
  };

  const handleResumeUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', userId);

    try {
      const response = await fetch(`${API_BASE_URL}/api/upload-resume`, {
        method: 'POST',
        body: formData
      });
      const analysis = await response.json();
      setResumeAnalysis(analysis);
      setIsEnhancedSuggestions(false); // Standard analysis, not enhanced
      setCurrentStep('post-upload-choice');
    } catch (error) {
      console.error('Error uploading resume:', error);
      alert('Error analyzing resume. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const selectCareerPath = async (careerPath) => {
    // Check if this career path has a low match score
    const isLowScore = await checkCareerPathScore(careerPath);
    
    if (isLowScore) {
      setWarningCareerPath(careerPath);
      setShowWarningDialog(true);
      return;
    }
    
    proceedWithCareerPath(careerPath);
  };

  const checkCareerPathScore = async (careerPath) => {
    // Calculate potential score for this career path
    setLoading(true);
    const formData = new FormData();
    formData.append('user_id', userId);
    formData.append('career_path', careerPath);

    try {
      const response = await fetch(`${API_BASE_URL}/api/calculate-career-score`, {
        method: 'POST',
        body: formData
      });
      const score = await response.json();
      setPotentialScore(score.current_score);
      
      // Return true if score is below 60 (low match)
      return score.current_score < 60;
    } catch (error) {
      console.error('Error checking career path score:', error);
      return false;
    } finally {
      setLoading(false);
    }
  };

  const proceedWithCareerPath = async (careerPath) => {
    setSelectedCareerPath(careerPath);
    
    try {
      await fetch(`${API_BASE_URL}/api/select-career-path`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          selected_career_path: careerPath
        })
      });
      
      calculateCareerScore(careerPath);
    } catch (error) {
      console.error('Error selecting career path:', error);
    }
  };

  const calculateCareerScore = async (careerPath) => {
    setLoading(true);
    const formData = new FormData();
    formData.append('user_id', userId);
    formData.append('career_path', careerPath);

    try {
      const response = await fetch(`${API_BASE_URL}/api/calculate-career-score`, {
        method: 'POST',
        body: formData
      });
      const score = await response.json();
      setCareerScore(score);
      setCurrentStep('career-score');
    } catch (error) {
      console.error('Error calculating career score:', error);
    } finally {
      setLoading(false);
    }
  };

  const addProgressLog = async (logEntry, activities, skills) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/progress-log`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          career_path: selectedCareerPath,
          log_entry: logEntry,
          activities_completed: activities || [],
          skills_improved: skills || []
        })
      });
      
      if (response.ok) {
        // Refresh user progress
        fetchUserProgress();
      }
    } catch (error) {
      console.error('Error adding progress log:', error);
    }
  };

  const fetchUserProgress = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/user-progress/${userId}`);
      const data = await response.json();
      if (data.career_score) {
        setCareerScore(data.career_score);
      }
      setProgressLogs(data.recent_logs || []);
    } catch (error) {
      console.error('Error fetching user progress:', error);
    }
  };

  const handleSurveySubmit = async () => {
    console.log('Survey submit started with responses:', surveyResponses);
    console.log('Number of responses:', Object.keys(surveyResponses).length);
    console.log('Required responses:', surveyQuestions.length);
    
    if (Object.keys(surveyResponses).length < surveyQuestions.length) {
      alert(`Please answer all ${surveyQuestions.length} questions before submitting.`);
      return;
    }
    
    setLoading(true);
    try {
      console.log('Submitting survey...');
      
      // Submit survey responses
      const surveyResponse = await fetch(`${API_BASE_URL}/api/submit-survey`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          responses: surveyResponses
        })
      });
      
      if (!surveyResponse.ok) {
        throw new Error(`Survey submission failed: ${surveyResponse.status}`);
      }
      
      console.log('Survey submitted successfully, getting enhanced suggestions...');
      
      // Get enhanced career suggestions based on survey responses
      const enhancedSuccess = await getEnhancedCareerSuggestions();
      
      if (enhancedSuccess) {
        console.log('Enhanced suggestions received, navigating to career suggestions...');
        setCurrentStep('career-suggestions');
      } else {
        console.log('Enhanced suggestions failed, falling back to regular suggestions...');
        setCurrentStep('career-suggestions');
      }
      
    } catch (error) {
      console.error('Error in survey submission flow:', error);
      alert('There was an issue processing your survey. Showing standard recommendations.');
      // Fallback to regular career suggestions if enhanced fails
      setCurrentStep('career-suggestions');
    } finally {
      setLoading(false);
    }
  };

  const getEnhancedCareerSuggestions = async () => {
    try {
      const formData = new FormData();
      formData.append('user_id', userId);
      
      const response = await fetch(`${API_BASE_URL}/api/enhanced-career-suggestions`, {
        method: 'POST',
        body: formData
      });
      
      if (response.ok) {
        const enhancedAnalysis = await response.json();
        console.log('Enhanced analysis received:', enhancedAnalysis);
        setResumeAnalysis(enhancedAnalysis);
        setIsEnhancedSuggestions(true); // Mark as enhanced suggestions
        return true;
      } else {
        console.error('Enhanced suggestions API call failed:', response.status);
        return false;
      }
    } catch (error) {
      console.error('Error getting enhanced suggestions:', error);
      return false;
    }
  };

  const fetchJobs = async () => {
    if (careerScore && careerScore.current_score >= 70) {
      try {
        const response = await fetch(`${API_BASE_URL}/api/mock-jobs/${selectedCareerPath}`);
        const data = await response.json();
        setJobs(data.jobs);
        setCurrentStep('jobs');
      } catch (error) {
        console.error('Error fetching jobs:', error);
      }
    } else {
      alert('You need a Career Score of 70+ to unlock job listings. Keep improving!');
    }
  };

  const renderWelcome = () => (
    <div className="step-container">
      <div className="hero-section">
        <h1 className="hero-title">🎯 NextObjective</h1>
        <p className="hero-subtitle">Transform your career with AI-powered guidance</p>
      </div>
      
      <div className="feature-grid">
        <div className="feature-card">
          <div className="feature-icon">📄</div>
          <h3>Resume Analysis</h3>
          <p>Upload your resume and get AI-powered career suggestions tailored to your experience</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon">🎯</div>
          <h3>Career Scoring</h3>
          <p>Get a detailed score showing how well you match your target career path</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon">📈</div>
          <h3>Progress Tracking</h3>
          <p>Log your daily progress and watch your career score improve over time</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon">💼</div>
          <h3>Job Matching</h3>
          <p>Unlock job opportunities when you reach your target career score</p>
        </div>
      </div>
      
      <button 
        onClick={() => setCurrentStep('upload')}
        className="btn-primary btn-large"
      >
        Get Started
      </button>
    </div>
  );

  const renderUpload = () => (
    <div className="step-container">
      <h2>Upload Your Resume</h2>
      <p className="step-description">Upload your resume (PDF or TXT) to get personalized career suggestions</p>
      
      <div className="upload-zone">
        <input
          type="file"
          accept=".pdf,.txt"
          onChange={handleResumeUpload}
          className="file-input"
          id="resume-upload"
        />
        <label htmlFor="resume-upload" className="upload-label">
          <div className="upload-icon">📄</div>
          <p>Click to upload your resume</p>
          <p className="upload-hint">PDF or TXT files only</p>
        </label>
      </div>
      
      {loading && (
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Analyzing your resume with AI...</p>
        </div>
      )}
    </div>
  );

  const renderPostUploadChoice = () => (
    <div className="step-container">
      <h2>✅ Resume Analysis Complete!</h2>
      <p className="step-description">
        We've analyzed your resume and identified potential career paths. 
        How would you like to proceed?
      </p>
      
      <div className="choice-cards">
        <div className="choice-card">
          <div className="choice-icon">📝</div>
          <h3>Take Preference Survey</h3>
          <p>Answer 10 questions about your work preferences to refine and personalize your career recommendations</p>
          <div className="enhancement-badge">✨ Enhanced AI Recommendations</div>
          <button 
            onClick={() => setCurrentStep('survey')}
            className="btn-primary"
          >
            Take Survey First
          </button>
        </div>
        
        <div className="choice-card">
          <div className="choice-icon">🚀</div>
          <h3>View Recommendations</h3>
          <p>See your AI-generated career suggestions based on your resume analysis right away</p>
          <button 
            onClick={() => setCurrentStep('career-suggestions')}
            className="btn-primary"
          >
            View Results Now
          </button>
        </div>
      </div>
      
      <div className="quick-stats">
        <h4>Your Resume Analysis Summary:</h4>
        <div className="stats-grid">
          <div className="stat-item">
            <span className="stat-number">{resumeAnalysis?.career_suggestions.length}</span>
            <span className="stat-label">Career Suggestions</span>
          </div>
          <div className="stat-item">
            <span className="stat-number">{resumeAnalysis?.extracted_skills.length}</span>
            <span className="stat-label">Skills Identified</span>
          </div>
          <div className="stat-item">
            <span className="stat-level">{resumeAnalysis?.experience_level}</span>
            <span className="stat-label">Experience Level</span>
          </div>
        </div>
      </div>
    </div>
  );

  const renderCareerSuggestions = () => {
    const filteredCareerPaths = careerPaths.filter(path =>
      path.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
      <div className="step-container">
        <h2>🎯 AI Career Suggestions</h2>
        <p className="step-description">Based on your resume analysis, here are the top career paths for you:</p>
        
        <div className="suggestions-grid">
          {resumeAnalysis?.career_suggestions.map((suggestion, index) => (
            <div key={index} className="suggestion-card">
              <div className="suggestion-header">
                <h3>{suggestion.career_path}</h3>
                <div className="match-score">
                  {Math.round(suggestion.match_score * 100)}% Match
                </div>
              </div>
              <p className="suggestion-reasoning">{suggestion.reasoning}</p>
              {isEnhancedSuggestions && suggestion.preference_match && (
                <div className="preference-match">
                  <h4>🎯 Preference Alignment:</h4>
                  <p>{suggestion.preference_match}</p>
                </div>
              )}
              <div className="skills-list">
                <h4>Key Skills:</h4>
                <div className="skills-tags">
                  {suggestion.key_skills.map((skill, i) => (
                    <span key={i} className="skill-tag">{skill}</span>
                  ))}
                </div>
              </div>
              <button 
                onClick={() => selectCareerPath(suggestion.career_path)}
                className="btn-primary"
              >
                Select This Path
              </button>
            </div>
          ))}
        </div>
        
        <div className="or-divider">
          <span>or search for any career path</span>
        </div>
        
        <div className="search-section">
          <div className="search-container">
            <input
              type="text"
              placeholder="Search for any career path..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
            <div className="search-icon">🔍</div>
          </div>
          
          <div className="career-paths-grid">
            {filteredCareerPaths.slice(0, 12).map((path, index) => (
              <button
                key={index}
                onClick={() => selectCareerPath(path)}
                className="career-path-btn"
              >
                {path}
              </button>
            ))}
          </div>
          
          {searchTerm && filteredCareerPaths.length === 0 && (
            <div className="no-results">
              <p>No career paths found matching "{searchTerm}"</p>
              <button 
                onClick={() => selectCareerPath(searchTerm)}
                className="btn-secondary"
              >
                Select "{searchTerm}" anyway
              </button>
            </div>
          )}
        </div>
        
        {loading && (
          <div className="loading-spinner">
            <div className="spinner"></div>
            <p>Calculating your career score...</p>
          </div>
        )}
      </div>
    );
  };

  const renderWarningDialog = () => (
    showWarningDialog && (
      <div className="dialog-overlay">
        <div className="dialog-box">
          <div className="dialog-header">
            <h3>⚠️ Low Match Warning</h3>
          </div>
          <div className="dialog-content">
            <p>
              Based on your resume analysis, <strong>{warningCareerPath}</strong> shows 
              a lower compatibility score of <strong>{potentialScore}/100</strong> with your current experience.
            </p>
            <p>
              This doesn't mean you can't pursue this path! It just means you may need more 
              preparation and skill development to be competitive in this field.
            </p>
          </div>
          <div className="dialog-actions">
            <button 
              onClick={() => {
                setShowWarningDialog(false);
                proceedWithCareerPath(warningCareerPath);
              }}
              className="btn-primary"
            >
              Proceed Anyway
            </button>
            <button 
              onClick={() => setShowWarningDialog(false)}
              className="btn-secondary"
            >
              Choose Different Path
            </button>
          </div>
        </div>
      </div>
    )
  );

  const renderCareerScore = () => (
    <div className="step-container">
      <h2>📊 Your Career Score</h2>
      <p className="step-description">Here's how well your current experience matches {selectedCareerPath}</p>
      
      <div className="score-card">
        <div className="score-circle">
          <div className="score-number">{careerScore?.current_score || 0}</div>
          <div className="score-label">/ 100</div>
        </div>
        <div className="score-details">
          <h3>Career Path: {selectedCareerPath}</h3>
          <p className="score-interpretation">
            {(careerScore?.current_score || 0) >= 80 ? "Excellent match!" :
             (careerScore?.current_score || 0) >= 60 ? "Good foundation, room for improvement" :
             "Significant growth opportunities ahead"}
          </p>
        </div>
      </div>
      
      <div className="analysis-sections">
        <div className="strength-section">
          <h3>💪 Your Strengths</h3>
          <ul>
            {careerScore?.strength_areas.map((strength, index) => (
              <li key={index}>{strength}</li>
            ))}
          </ul>
        </div>
        
        <div className="gaps-section">
          <h3>🎯 Areas to Improve</h3>
          <ul>
            {careerScore?.skill_gaps.map((gap, index) => (
              <li key={index}>{gap}</li>
            ))}
          </ul>
        </div>
        
        <div className="recommendations-section">
          <h3>🚀 Recommendations</h3>
          <ul>
            {careerScore?.recommendations.map((rec, index) => (
              <li key={index}>{rec}</li>
            ))}
          </ul>
        </div>
      </div>
      
      <div className="action-buttons">
        <button 
          onClick={() => setCurrentStep('survey')}
          className="btn-secondary"
        >
          Take Preference Survey
        </button>
        <button 
          onClick={() => setCurrentStep('progress')}
          className="btn-primary"
        >
          Start Progress Tracking
        </button>
      </div>
    </div>
  );

  const renderSurvey = () => (
    <div className="step-container">
      <h2>📝 Career Preferences Survey</h2>
      <p className="step-description">Help us refine your career recommendations with personalized preferences</p>
      
      <div className="survey-progress">
        <div className="progress-text">
          Progress: {Object.keys(surveyResponses).length} / {surveyQuestions.length} questions completed
        </div>
        <div className="progress-bar">
          <div 
            className="progress-fill" 
            style={{width: `${(Object.keys(surveyResponses).length / surveyQuestions.length) * 100}%`}}
          ></div>
        </div>
      </div>
      
      <div className="survey-questions">
        {surveyQuestions.map((question) => (
          <div key={question.id} className="question-card">
            <h3>{question.question}</h3>
            {question.type === 'multiple_choice' ? (
              <div className="options-grid">
                {question.options.map((option, index) => (
                  <button
                    key={index}
                    onClick={() => setSurveyResponses({
                      ...surveyResponses,
                      [question.id]: option
                    })}
                    className={`option-btn ${surveyResponses[question.id] === option ? 'selected' : ''}`}
                  >
                    {option}
                  </button>
                ))}
              </div>
            ) : (
              <div className="scale-container">
                <span>{question.labels[0]}</span>
                <input
                  type="range"
                  min={question.min}
                  max={question.max}
                  value={surveyResponses[question.id] || Math.ceil((question.min + question.max) / 2)}
                  onChange={(e) => setSurveyResponses({
                    ...surveyResponses,
                    [question.id]: parseInt(e.target.value)
                  })}
                  className="scale-slider"
                />
                <span>{question.labels[1]}</span>
                <div className="scale-value">
                  Current: {surveyResponses[question.id] || Math.ceil((question.min + question.max) / 2)}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
      
      <button 
        onClick={handleSurveySubmit}
        className="btn-primary"
        disabled={Object.keys(surveyResponses).length < surveyQuestions.length || loading}
      >
        {loading ? 'Creating Enhanced Recommendations...' : 'Complete Survey'}
      </button>
      
      {loading && (
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Analyzing your preferences and creating personalized career recommendations...</p>
        </div>
      )}
    </div>
  );

  const renderProgress = () => {
    const handleAddLog = () => {
      if (newLog.trim()) {
        addProgressLog(
          newLog,
          activities.split(',').map(a => a.trim()).filter(a => a),
          skills.split(',').map(s => s.trim()).filter(s => s)
        );
        setNewLog('');
        setActivities('');
        setSkills('');
      }
    };

    return (
      <div className="step-container">
        <h2>📈 Progress Tracking</h2>
        <p className="step-description">Log your daily progress toward your career goals</p>
        
        <div className="current-score-banner">
          <h3>Current Career Score: {careerScore?.current_score || 0}/100</h3>
          <div className="score-bar">
            <div 
              className="score-fill" 
              style={{width: `${careerScore?.current_score || 0}%`}}
            ></div>
          </div>
        </div>
        
        <div className="progress-form">
          <h3>Add Today's Progress</h3>
          <textarea
            value={newLog}
            onChange={(e) => setNewLog(e.target.value)}
            placeholder="What did you accomplish today toward your career goals?"
            className="log-textarea"
          />
          <input
            type="text"
            value={activities}
            onChange={(e) => setActivities(e.target.value)}
            placeholder="Activities completed (comma-separated)"
            className="log-input"
          />
          <input
            type="text"
            value={skills}
            onChange={(e) => setSkills(e.target.value)}
            placeholder="Skills improved (comma-separated)"
            className="log-input"
          />
          <button onClick={handleAddLog} className="btn-primary">
            Log Progress
          </button>
        </div>
        
        <div className="progress-history">
          <h3>Recent Progress</h3>
          {progressLogs.length > 0 ? (
            progressLogs.map((log, index) => (
              <div key={index} className="log-entry">
                <div className="log-date">
                  {new Date(log.timestamp).toLocaleDateString()}
                </div>
                <div className="log-content">{log.log_entry}</div>
                {log.activities_completed.length > 0 && (
                  <div className="log-activities">
                    <strong>Activities:</strong> {log.activities_completed.join(', ')}
                  </div>
                )}
                {log.skills_improved.length > 0 && (
                  <div className="log-skills">
                    <strong>Skills:</strong> {log.skills_improved.join(', ')}
                  </div>
                )}
              </div>
            ))
          ) : (
            <p>No progress logged yet. Start tracking your journey!</p>
          )}
        </div>
        
        <div className="action-buttons">
          <button 
            onClick={fetchJobs}
            className="btn-primary"
            disabled={!careerScore || careerScore.current_score < 70}
          >
            {careerScore && careerScore.current_score >= 70 ? 
              'View Job Opportunities' : 
              `Unlock Jobs at 70+ Score (Current: ${careerScore?.current_score || 0})`
            }
          </button>
        </div>
      </div>
    );
  };

  const renderJobs = () => (
    <div className="step-container">
      <h2>💼 Job Opportunities</h2>
      <p className="step-description">Congratulations! You've unlocked job listings for {selectedCareerPath}</p>
      
      <div className="jobs-grid">
        {jobs.map((job, index) => (
          <div key={index} className="job-card">
            <div className="job-header">
              <h3>{job.title}</h3>
              <div className="company-info">
                <strong>{job.company}</strong>
                <span className="location">{job.location}</span>
              </div>
            </div>
            <p className="job-description">{job.description}</p>
            <div className="job-requirements">
              <h4>Requirements:</h4>
              <ul>
                {job.requirements.map((req, i) => (
                  <li key={i}>{req}</li>
                ))}
              </ul>
            </div>
            {job.salary_range && (
              <div className="salary-range">
                <strong>Salary:</strong> {job.salary_range}
              </div>
            )}
            <button 
              onClick={() => window.open(job.url, '_blank')}
              className="btn-primary"
            >
              Apply Now
            </button>
          </div>
        ))}
      </div>
      
      <button 
        onClick={() => setCurrentStep('progress')}
        className="btn-secondary"
      >
        Back to Progress Tracking
      </button>
    </div>
  );

  const renderCurrentStep = () => {
    switch (currentStep) {
      case 'welcome': return renderWelcome();
      case 'upload': return renderUpload();
      case 'post-upload-choice': return renderPostUploadChoice();
      case 'career-suggestions': return renderCareerSuggestions();
      case 'career-score': return renderCareerScore();
      case 'survey': return renderSurvey();
      case 'progress': return renderProgress();
      case 'jobs': return renderJobs();
      default: return renderWelcome();
    }
  };

  return (
    <div className="App">
      <nav className="navbar">
        <div className="nav-brand">🎯 NextObjective</div>
        <div className="nav-menu">
          <button 
            onClick={() => setCurrentStep('progress')}
            className="nav-link"
            disabled={!selectedCareerPath}
          >
            Dashboard
          </button>
          <button 
            onClick={() => setCurrentStep('welcome')}
            className="nav-link"
          >
            Home
          </button>
        </div>
      </nav>
      
      <main className="main-content">
        {renderCurrentStep()}
      </main>
      
      {renderWarningDialog()}
      
      <footer className="footer">
        <p>&copy; 2025 NextObjective. Transform your career with AI.</p>
      </footer>
    </div>
  );
}

export default App;