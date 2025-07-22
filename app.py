# In app.py
from flask import Flask, render_template, request, redirect, url_for, session, jsonify # Removed send_file, send_from_directory as they are not needed for templates
import os # Still needed for os.makedirs and potential other path operations
import datetime
import uuid

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here' # **CRITICAL: Change this to a strong, random key in production**

# --- Mock Database / Data Storage ---
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

mock_session_logs = {
    "YOUTH001": [
        {"session_id": "sess_1", "module": "Intro", "date": "2025-07-20", "status": "completed", "video_path": "mock_video_uploads/video_Y001_S1.mp4", "reflection": "Learned about introductions."},
        {"session_id": "sess_2", "module": "Anger Management", "date": "2025-07-21", "status": "completed", "video_path": "mock_video_uploads/video_Y001_S2.mp4", "reflection": "Reflected on anger triggers."}
    ],
    "YOUTH002": [
        {"session_id": "sess_3", "module": "Job Prep", "date": "2025-07-19", "status": "completed", "video_path": "mock_video_uploads/video_Y002_S3.mp4", "reflection": "Updated resume tips."}
    ]
}

mock_pilot_applications_db = {} # Stores submitted pilot applications

# --- Utility Functions (Mocked) ---
def verify_identity_mock(video_stream_data, expected_user_id):
    """
    Mock function for identity verification.
    In a real system, this would involve AI/ML for face/voice recognition.
    """
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
    """
    video_filename = f"youth_{youth_id}_session_{session_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.mp4"
    upload_folder = 'mock_video_uploads'
    os.makedirs(upload_folder, exist_ok=True)
    mock_file_path = os.path.join(upload_folder, video_filename)

    # For mock, video_data is a base64 string. We'll just write a dummy file.
    # In a real app, you'd decode base64 and write actual binary video data.
    with open(mock_file_path, "wb") as f:
        f.write(f"Mock video content for {youth_id} session {session_id}".encode('utf-8'))

    print(f"Mock: Video for {youth_id}, session {session_id} saved to {mock_file_path} and 'uploaded' to court contacts.")
    return mock_file_path

# --- Routes ---

@app.route('/')
def homepage():
    """
    Renders the public-facing homepage (home.html) or redirects to the dashboard
    if the user is already logged in.
    """
    if 'user_id' in session:
        # If logged in, redirect to the combined dashboard (index.html)
        return redirect(url_for('dashboard'))
    
    # If not logged in, render the public homepage template
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user (youth or admin) login."""
    user_id = request.form.get('user_id')
    password = request.form.get('password')
    user_type_field = request.form.get('user_type_field')

    message = None

    if request.method == 'POST':
        if user_type_field == 'youth':
            device_id = request.form.get('device_id')
            if user_id in mock_youth_db and mock_youth_db[user_id]['device_id'] == device_id:
                session['user_id'] = user_id
                session['user_role'] = 'youth'
                return redirect(url_for('dashboard')) # Redirect to combined dashboard
            else:
                message = "Invalid Youth ID or Device ID."
                user_type = 'youth'
        elif user_type_field == 'admin':
            if user_id in mock_admin_db and mock_admin_db[user_id]['password'] == password:
                session['user_id'] = user_id
                session['user_role'] = mock_admin_db[user_id]['role'].lower().replace(' ', '_')
                return redirect(url_for('dashboard')) # Redirect to combined dashboard
            else:
                message = "Invalid Admin/Judge ID or Password."
                user_type = 'admin'
        else:
            message = "Invalid login attempt."
            user_type = 'youth'

        return render_template('login.html', message=message, user_type=user_type)

    user_type = request.args.get('type', 'youth')
    return render_template('login.html', user_type=user_type)

@app.route('/logout')
def logout():
    """Logs the user out by clearing the session."""
    session.pop('user_id', None)
    session.pop('user_role', None)
    return redirect(url_for('homepage')) # Redirect to the public homepage after logout

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    Renders the signup page and handles pilot application submission.
    This is for organizations/courts to sign up for a pilot, not individual youth.
    """
    message = None
    if request.method == 'POST':
        org_name = request.form.get('organization_name')
        contact_person = request.form.get('contact_person')
        contact_email = request.form.get('contact_email')
        phone_number = request.form.get('phone_number')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not all([org_name, contact_person, contact_email, password, confirm_password]):
            message = "All required fields must be filled."
        elif password != confirm_password:
            message = "Passwords do not match."
        elif contact_email in [app['contact_email'] for app in mock_pilot_applications_db.values()]:
            message = "An application with this email already exists."
        else:
            application_id = str(uuid.uuid4())
            mock_pilot_applications_db[application_id] = {
                "organization_name": org_name,
                "contact_person": contact_person,
                "contact_email": contact_email,
                "phone_number": phone_number,
                "password_hash": "MOCKED_HASH_" + password, # Simulate hashing
                "status": "pending",
                "application_date": datetime.date.today().isoformat()
            }
            message = "Pilot application submitted successfully! We will review your application and contact you soon."
            return render_template('signup.html', message=message, success=True)
            
    return render_template('signup.html', message=message)

# --- Combined Dashboard Route ---
@app.route('/dashboard')
def dashboard():
    """
    Renders the combined dashboard (index.html) based on user role.
    This replaces separate youth_dashboard and admin_dashboard routes for rendering.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_role = session['user_role']
    user_id = session['user_id']

    if user_role == 'youth':
        youth_data = mock_youth_db.get(user_id)
        if not youth_data:
            return "Youth data not found.", 404
        next_module_info = {
            "name": youth_data['current_module'],
            "description": f"Complete your daily session for {youth_data['current_module']}."
        }
        recent_sessions = mock_session_logs.get(user_id, [])[-3:]
        return render_template('index.html',
                               youth=youth_data,
                               next_module=next_module_info,
                               recent_sessions=recent_sessions,
                               now=datetime.datetime.now)
    elif user_role in ['admin', 'judge']:
        admin_data = mock_admin_db.get(user_id)
        if not admin_data:
            return "Admin/Judge data not found.", 404
        accessible_youth_ids = admin_data.get('assigned_youth', [])
        youth_list = [
            {'id': uid, **mock_youth_db[uid], 'recent_sessions': mock_session_logs.get(uid, [])[-1:]}
            for uid in accessible_youth_ids if uid in mock_youth_db
        ]
        return render_template('index.html',
                               admin=admin_data,
                               youth_list=youth_list,
                               now=datetime.datetime.now)
    else:
        return "Unauthorized role.", 403


# --- Youth-Specific Routes (for actions, not direct rendering of dashboard) ---
@app.route('/youth_session/<module_name>')
def youth_session(module_name):
    """
    Renders the page for a specific rehabilitation module session.
    """
    if 'user_id' not in session or session['user_role'] != 'youth':
        return redirect(url_for('login'))

    youth_id = session['user_id']
    module_content = {
        "title": module_name,
        "video_prompt_url": "https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1&controls=0",
        "reflection_question": f"What did you learn from today's {module_name} session and how will you apply it?",
        "quiz_url": "/quiz/anger_management"
    }

    return render_template('youth_session.html',
                           youth_id=youth_id,
                           module=module_content)

@app.route('/submit_session_data', methods=['POST'])
def submit_session_data():
    """
    Handles the submission of session data (video, reflection, quiz results).
    """
    if 'user_id' not in session or session['user_role'] != 'youth':
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    youth_id = session['user_id']
    module_name = request.form.get('module_name')
    reflection = request.form.get('reflection_text')
    video_blob = request.form.get('video_data')

    if not all([module_name, reflection, video_blob]):
        return jsonify({"success": False, "message": "Missing required session data"}), 400

    identity_ok, identity_msg = verify_identity_mock(video_blob, youth_id)
    if not identity_ok:
        return jsonify({"success": False, "message": identity_msg}), 403

    session_uuid = str(uuid.uuid4())
    mock_video_path = store_video_and_upload_to_court_mock(youth_id, session_uuid, video_blob)

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

    if youth_id in mock_youth_db:
        mock_youth_db[youth_id]['sessions_completed'] += 1

    return jsonify({"success": True, "message": "Session submitted successfully!", "session_id": session_uuid})

# --- Admin/Judge Specific Routes (for actions, not direct rendering of dashboard) ---
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
    base_dir = os.path.abspath(os.path.dirname(__file__))
    full_path = os.path.join(base_dir, video_path)

    # Make sure the video path is within the designated mock_video_uploads folder
    # and that the file actually exists.
    if not os.path.exists(full_path) or not full_path.startswith(os.path.join(base_dir, 'mock_video_uploads')):
        return "Video not found or unauthorized.", 404

    return send_file(full_path, mimetype='video/mp4')

# --- Run the App ---
if __name__ == '__main__':
    os.makedirs('mock_video_uploads', exist_ok=True)
    app.run(debug=True)
