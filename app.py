from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import os
import datetime
import uuid # For generating unique IDs

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here' # **CRITICAL: Change this to a strong, random key in production**

# --- Mock Database / Data Storage ---
# In a real application, you would use a proper database (e.g., PostgreSQL, MySQL, MongoDB)
# and an ORM (e.g., SQLAlchemy) for persistent storage.

mock_youth_db = {
    "YOUTH001": {
        "device_id": "DEVICEABC",
        "name": "Alex Smith",
        "court_id": "COURT123",
        "probation_officer": "PO_JaneDoe",
        "current_module": "Anger Management",
        "sessions_completed": 5,
        "required_sessions": 30,
        "status": "active"
    },
    "YOUTH002": {
        "device_id": "DEVICEXYZ",
        "name": "Jordan Lee",
        "court_id": "COURT123",
        "probation_officer": "PO_JaneDoe",
        "current_module": "Job Prep",
        "sessions_completed": 12,
        "required_sessions": 30,
        "status": "active"
    }
}

mock_admin_db = {
    "PO_JaneDoe": {
        "password": "adminpassword", # **NEVER store plain passwords in production**
        "name": "Jane Doe",
        "role": "Probation Officer",
        "assigned_youth": ["YOUTH001", "YOUTH002"]
    },
    "Judge_Roberts": {
        "password": "judgepassword",
        "name": "Judge Roberts",
        "role": "Judge",
        "assigned_youth": ["YOUTH001"] # Can view specific youth data
    }
}

# This would store references to uploaded videos, not the videos themselves in memory
mock_session_logs = {
    "YOUTH001": [
        {"session_id": "sess_1", "module": "Intro", "date": "2025-07-20", "status": "completed", "video_path": "path/to/video_Y001_S1.mp4", "reflection": "Learned about introductions."},
        {"session_id": "sess_2", "module": "Anger Management", "date": "2025-07-21", "status": "completed", "video_path": "path/to/video_Y001_S2.mp4", "reflection": "Reflected on anger triggers."}
    ],
    "YOUTH002": [
        {"session_id": "sess_3", "module": "Job Prep", "date": "2025-07-19", "status": "completed", "video_path": "path/to/video_Y002_S3.mp4", "reflection": "Updated resume tips."}
    ]
}

# --- Utility Functions (Mocked) ---

def verify_identity_mock(video_stream_data, expected_user_id):
    """
    Mock function for identity verification.
    In a real system, this would involve AI/ML for face/voice recognition.
    """
    # Simulate a check, e.g., 90% chance of success for correct ID
    import random
    if random.random() < 0.9:
        print(f"Identity for {expected_user_id} verified successfully (mock).")
        return True, "Identity Verified"
    else:
        print(f"Identity for {expected_user_id} verification failed (mock).")
        return False, "Identity Mismatch Detected"

def store_video_and_upload_to_court_mock(youth_id, session_id, video_data):
    """
    Mock function to simulate secure video storage and upload.
    In reality, this would involve:
    1. Saving video to secure cloud storage (AWS S3, Google Cloud Storage).
    2. Encrypting video.
    3. Sending a secure link/notification to court contacts.
    4. Deleting local/temp file after upload.
    """
    video_filename = f"youth_{youth_id}_session_{session_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.mp4"
    # Create a dummy directory for mock video files
    upload_folder = 'mock_video_uploads'
    os.makedirs(upload_folder, exist_ok=True)
    mock_file_path = os.path.join(upload_folder, video_filename)

    # Simulate saving a file (in a real scenario, video_data would be actual bytes)
    with open(mock_file_path, "wb") as f:
        f.write(b"Mock video content for " + video_data.encode('utf-8')) # Simulate writing binary data

    print(f"Mock: Video for {youth_id}, session {session_id} saved to {mock_file_path} and 'uploaded' to court contacts.")
    return mock_file_path # Return a mock path


# --- Routes ---

@app.route('/')
def index():
    """Renders the main landing page or redirects to login."""
    if 'user_id' in session:
        if session['user_role'] == 'youth':
            return redirect(url_for('youth_dashboard'))
        elif session['user_role'] == 'admin' or session['user_role'] == 'judge':
            return redirect(url_for('admin_dashboard'))
    return render_template('index.html') # This would be your public landing page (or a login page)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user (youth or admin) login."""
    if request.method == 'POST':
        user_id = request.form['user_id'].strip()
        password = request.form.get('password') # Only admins/judges have passwords in this mock

        # Attempt Youth Login (by ID and device_id)
        if user_id in mock_youth_db:
            device_id = request.form.get('device_id')
            if mock_youth_db[user_id]['device_id'] == device_id:
                session['user_id'] = user_id
                session['user_role'] = 'youth'
                return redirect(url_for('youth_dashboard'))
            else:
                return render_template('login.html', message="Invalid device ID for youth.", user_type="youth")

        # Attempt Admin/Judge Login
        elif user_id in mock_admin_db:
            if mock_admin_db[user_id]['password'] == password: # **Insecure, use hashed passwords!**
                session['user_id'] = user_id
                session['user_role'] = mock_admin_db[user_id]['role'].lower().replace(' ', '_')
                return redirect(url_for('admin_dashboard'))
            else:
                return render_template('login.html', message="Invalid username or password.", user_type="admin")
        else:
            return render_template('login.html', message="User not found.", user_type="both")

    # Determine what login form to show if GET request
    user_type = request.args.get('type', 'youth') # Default to youth login
    return render_template('login.html', user_type=user_type)

@app.route('/logout')
def logout():
    """Logs the user out by clearing the session."""
    session.pop('user_id', None)
    session.pop('user_role', None)
    return redirect(url_for('login'))

# --- Youth-Specific Routes ---

@app.route('/youth_dashboard')
def youth_dashboard():
    """Displays the youth's personalized dashboard with daily goals."""
    if 'user_id' not in session or session['user_role'] != 'youth':
        return redirect(url_for('login'))

    youth_id = session['user_id']
    youth_data = mock_youth_db.get(youth_id)
    if not youth_data:
        return "Youth data not found.", 404

    # Get the next module or current module status
    # In a real app, this would be more dynamic based on progress
    next_module_info = {
        "name": youth_data['current_module'],
        "description": f"Complete your daily session for {youth_data['current_module']}."
    }
    
    # Get recent sessions for display
    recent_sessions = mock_session_logs.get(youth_id, [])[-3:] # Last 3 sessions

    return render_template('youth_dashboard.html',
                           youth=youth_data,
                           next_module=next_module_info,
                           recent_sessions=recent_sessions)


@app.route('/youth_session/<module_name>')
def youth_session(module_name):
    """
    Renders the page for a specific rehabilitation module session.
    This would embed video prompts, reflection questions, etc.
    """
    if 'user_id' not in session or session['user_role'] != 'youth':
        return redirect(url_for('login'))

    youth_id = session['user_id']
    # You'd load module content from a separate data source/DB here
    module_content = {
        "title": module_name,
        "video_prompt_url": "https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1&controls=0", # Example embed
        "reflection_question": f"What did you learn from today's {module_name} session and how will you apply it?",
        "quiz_url": "/quiz/anger_management" # Placeholder for a quiz
    }

    return render_template('youth_session.html',
                           youth_id=youth_id,
                           module=module_content)

@app.route('/submit_session_data', methods=['POST'])
def submit_session_data():
    """
    Handles the submission of session data (video, reflection, quiz results).
    This is where the core compliance tracking happens.
    """
    if 'user_id' not in session or session['user_role'] != 'youth':
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    youth_id = session['user_id']
    module_name = request.form.get('module_name')
    reflection = request.form.get('reflection_text')
    video_blob = request.form.get('video_data') # This would be actual file data in production

    if not all([module_name, reflection, video_blob]):
        return jsonify({"success": False, "message": "Missing required session data"}), 400

    # 1. Identity Verification (Mocked)
    identity_ok, identity_msg = verify_identity_mock(video_blob, youth_id)
    if not identity_ok:
        return jsonify({"success": False, "message": identity_msg}), 403

    # 2. Store Video and Upload to Court Contacts (Mocked)
    session_uuid = str(uuid.uuid4()) # Unique ID for this session submission
    mock_video_path = store_video_and_upload_to_court_mock(youth_id, session_uuid, video_blob)

    # 3. Log Session Completion
    if youth_id not in mock_session_logs:
        mock_session_logs[youth_id] = []

    mock_session_logs[youth_id].append({
        "session_id": session_uuid,
        "module": module_name,
        "date": datetime.date.today().isoformat(),
        "status": "completed",
        "video_path": mock_video_path,
        "reflection": reflection,
        "identity_status": identity_msg
    })

    # Update youth's progress
    if youth_id in mock_youth_db:
        mock_youth_db[youth_id]['sessions_completed'] += 1
        # Logic to advance module or set next module based on completion
        # For simplicity, we just increment completed sessions

    return jsonify({"success": True, "message": "Session submitted successfully!", "session_id": session_uuid})

# --- Admin/Judge Specific Routes ---

@app.route('/admin_dashboard')
def admin_dashboard():
    """Displays the admin/judge dashboard with an overview of youth progress."""
    if 'user_id' not in session or (session['user_role'] != 'admin' and session['user_role'] != 'judge'):
        return redirect(url_for('login'))

    admin_id = session['user_id']
    admin_data = mock_admin_db.get(admin_id)

    # Filter youth data based on who the admin/judge is assigned to
    accessible_youth_ids = admin_data.get('assigned_youth', [])
    youth_list = [
        {'id': uid, **mock_youth_db[uid], 'recent_sessions': mock_session_logs.get(uid, [])[-1:]} # Get last session
        for uid in accessible_youth_ids if uid in mock_youth_db
    ]

    return render_template('admin_dashboard.html',
                           admin=admin_data,
                           youth_list=youth_list)

@app.route('/admin/youth_details/<youth_id>')
def youth_details(youth_id):
    """
    Displays detailed information and session history for a specific youth.
    Includes links to mock video evidence.
    """
    if 'user_id' not in session or (session['user_role'] != 'admin' and session['user_role'] != 'judge'):
        return redirect(url_for('login'))

    admin_id = session['user_id']
    admin_data = mock_admin_db.get(admin_id)

    # Security check: Ensure admin/judge is authorized to view this youth
    if youth_id not in admin_data.get('assigned_youth', []):
        return "Unauthorized to view this youth's details.", 403

    youth_data = mock_youth_db.get(youth_id)
    session_history = mock_session_logs.get(youth_id, [])

    if not youth_data:
        return "Youth data not found.", 404

    return render_template('youth_details.html',
                           youth=youth_data,
                           session_history=session_history)

@app.route('/view_video/<path:video_path>')
def view_video(video_path):
    """
    Mocks serving a video file. In a real application, this would stream from secure cloud storage.
    """
    # This is highly simplified and would need proper security (e.g., signed URLs)
    # and handling for various video formats.
    
    # Ensure the path is within the designated mock upload folder for security
    base_dir = os.path.abspath(os.path.dirname(__file__))
    full_path = os.path.join(base_dir, video_path)

    if not os.path.exists(full_path) or not full_path.startswith(os.path.join(base_dir, 'mock_video_uploads')):
        return "Video not found or unauthorized.", 404

    # For demonstration, assume it's an MP4. In real life, check content type.
    return send_file(full_path, mimetype='video/mp4')


# --- Run the App ---
if __name__ == '__main__':
    # Create the mock_video_uploads directory if it doesn't exist
    os.makedirs('mock_video_uploads', exist_ok=True)
    app.run(debug=True) # debug=True is for development only, set to False in production
