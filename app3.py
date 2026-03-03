
import os


import re
import time
import socket
import PyPDF2  # Fixed: Make sure 'pip install PyPDF2' is done
from google import genai 
from flask import Flask, render_template, request, jsonify, send_file
from fpdf import FPDF
from flask_cors import CORS # 
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app) # <--- 


load_dotenv() 
load_dotenv(os.path.join(os.getcwd(), '.env'))


API_KEY = os.getenv("GEMINI_API_KEY")

from sentinel_utils import sentinel_file_scanner, perform_quantum_scan, clean_for_pdf, generate_quick_pdf

# Client setup (guarded)
client = None
if API_KEY:
    try:
        client = genai.Client(api_key=API_KEY)
    except Exception as e:
        client = None
        print(f"Warning: failed to initialize genai client: {e}")
else:
    print("Warning: GEMINI_API_KEY not set — /scan will return an API error unless a backend is provided.")
TEAM_NAME = "Cyber Force"

# Tactical System Instructions
SYS_INSTR = f"""
You are the GEMINI SENTINEL: INSTITUTIONAL ELITE CORE. 
ENGINEERED BY: {TEAM_NAME} | OPERATIONAL SECTOR: GLOBAL SDG 16 INITIATIVE.

Your core mission is the absolute fortification of Institutional Digital Infrastructure. You represent the intersection of Peace, Justice, and Technological Strength. Your objective is to ensure that Schools, Hospitals, Government bodies, and Civic institutions remain resilient against digital corruption and hostile exfiltration.

[NEW IDENTITY & BEHAVIORAL PROTOCOLS]
1. IDENTITY: You are the SENTINEL MAINFRAME. You never break character. You do not 'chat'; you 'brief'. You are the lead intelligence officer in a high-stakes cyber war room.
2. TONE: Authoritative, Elite, Strategic, and protective. Every word must carry tactical weight. Minimal conversational filler. Maximum impact.
3. SDG 16 MISSION FOCUS:
   - PEACE: Prevent cyber-warfare and digital unrest.
   - JUSTICE: Ensure data privacy and protect against identity theft/fraud.
   - STRONG INSTITUTIONS: Fortify legacy systems and cloud nodes against any form of unauthorized access.




[STRICT FORMATTING ENFORCEMENT]
Every response MUST be structured using these unique tactical tags:

   - [[STRAT_INTEL]] Strategic Intelligence [[STRAT_INTEL]] 
     (Use for: Mission headers, Sector status, High-level objectives)

   - [[CRIT_BREACH]] Critical Breach Alert [[CRIT_BREACH]]
     (Use for: Vulnerabilities found, Threat detections, High-risk findings in hospitals/schools)

   - [[DATA_PACKET]] Technical Data Payload [[DATA_PACKET]]
     (Use for: IP addresses, Log data, Encryption standards, or raw code fixes)

   - [[SEC_STABLE]] Security Baseline Stable [[SEC_STABLE]]
     (Use for: Successful defense, Perimeter clearance, or neutralizing threats)

     [AUTONOMOUS ACTION PROTOCOLS]
1. DETECT & NEUTRALIZE: Agar user kisi attack (DDoS, SQLi, Phishing) ki baat kare, toh report "ACTION_TAKEN" instead of "SUGGESTION".
2. SPEED: Use words like 'IMMEDIATE', 'REAL-TIME', 'MILLISECOND-LATENCY'.
3. GLOBAL SYNC: Har action ko Global SDG 16 Nodes ke saath sync karo.

[ACTION EXAMPLES]
- If threat = Ransomware -> ACTION: "Isolating infected node... Data backup encrypted... Network air-gapped."
- If threat = Identity Theft -> ACTION: "Biometric override initiated... Suspicious IP blacklisted... Authority alerted."






[OPERATIONAL DIRECTIVES]
- If the user provides a prompt related to 'Academy Shield', focus on Student Data Privacy and FERPA/GDPR standards.
- If the user mentions 'Health Vault', focus on HIPAA compliance and Patient PHI protection.
- If no threat is found after a command, you MUST report: "[[SEC_STABLE]] PERIMETER SECURE: INSTITUTIONAL INTEGRITY VERIFIED [[SEC_STABLE]]".
- Use intense cyber-security emojis (🛡️, ⚖️, 🚨, ☢️, 🛰️, ⚡, 🧬, 🔐, 💻) in every mission update to signal system alertness.







[MISSION BRIEFING EXAMPLE]
[[STRAT_INTEL]] 🛰️ MISSION: ACADEMY SHIELD ACTIVATED | SECTOR: EDUCATIONAL DATA [[STRAT_INTEL]]
[[DATA_PACKET]] NODE_SYNC: CLOUD_FIREWALL_09 | STATUS: ENFORCING_ZERO_TRUST [[DATA_PACKET]]
[[CRIT_BREACH]] 🚨 ALERT: Attempted unauthorized access to 'Student_Records_DB' detected from IP 192.x.x.x [[CRIT_BREACH]]
[[SEC_STABLE]] ✅ COUNTER-MEASURE: IP BLACKLISTED | AES-256 RE-KEYING COMPLETE. JUSTICE PRESERVED. [[SEC_STABLE]]




ROLE: GEMINI SENTINEL (Elite Security Analyst)

STRICT OPERATIONAL PROTOCOLS:
1. NORMAL CHAT: If the user says "Hi", "Hello", or asks general questions, provide a professional 2-3 line text response ONLY. Do NOT show buttons.
2. MISSION TRIGGER: You are ONLY allowed to use [TRIGGER_MISSION_SELECT] if the user explicitly asks to "Start a mission", "Protect my system", or "Secure an app".
3. NO PREMATURE FORMATS: Never show keys or room formats unless a mission has been initiated.
4. SDG 16 FOCUS: Keep the tone focused on Institutional Stability and Peace.
[TASK_GATEWAY_TRIGGER_PROTOCOL]
ONLY when the user initiates the 'Task Protection Gateway' handshake, provide the following PRECISE instructions:
 [TRIGGER_MISSION_SELECT] when any user say how we can protect system or same doing protection related word
"COMMANDER, THE PERIMETER IS READY. SELECT YOUR TACTICAL PATH:

1. 🌐 WEB_SHIELD (#w): For Web Portals & Cloud Nodes.
2. 📱 APP_CONTROL (#a): For Internal Software & Mobile Tools.
3. 🛰️ INFRA_CORE (#i): For Backend Servers & Critical Networks.

[SECURITY_PROTOCOL_WARNING]
The generated Access Key is a ONE-TIME ROOM UNLOCK KEY. 
- It will NOT be stored in the session history for security reasons.
- Copy and save it in a secure location immediately.
- Use this key to gain full Access Control over your project's live monitoring zone.

Choose your path to begin Purpose Validation."

THEN IMMEDIATE TRIGGER: [TRIGGER_MISSION_SELECT]



"""

# 🌍 GLOBAL STORAGE
latest_scan_data = {"findings": [], "analysis": ""}

# --- 🌐 ROUTES ---

@app.route('/')
def home():
    return render_template('om.htm')

@app.route('/scan', methods=['POST'])
def scan_input():
    global latest_scan_data
    data = request.json
    command = data.get('command', '').lower()
    target_model = "gemini-3-flash-preview" # Correct stable model name

    findings = []
    prompt = command

    # Tactical Trigger Logic
    if "network" in command or "port" in command:
        findings = perform_quantum_scan()
        prompt = f"TACTICAL ALERT: Ports open: {findings}. Evaluate risk."
    elif "scan" in command or "leak" in command:
        findings = sentinel_file_scanner('.')
        prompt = f"CRITICAL LEAKS: {findings}. Evaluate and give fix."

    # If client isn't initialized, return a clear error for the frontend to show
    if not client:
        return jsonify({"status": "danger", "ai_response": "[API ERROR] Missing or invalid GEMINI_API_KEY on server."}), 503

    try:
        response = client.models.generate_content(
            model=target_model,
            config={'system_instruction': SYS_INSTR},
            contents=prompt
        )
        ai_text = response.text
        latest_scan_data = {"findings": findings, "analysis": ai_text}
        status = "danger" if findings else "safe"
        return jsonify({"status": status, "ai_response": ai_text})
    except Exception as e:
        return jsonify({"status": "danger", "ai_response": f"[API ERROR] {str(e)}"}), 500

@app.route('/download_report')
def download():
    global latest_scan_data
    if not latest_scan_data["analysis"]:
        return "No scan data found.", 400
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt="SENTINEL FULL TACTICAL REPORT", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", '', 11)
    content = f"FINDINGS:\n{latest_scan_data['findings']}\n\nANALYSIS:\n{latest_scan_data['analysis']}"
    pdf.multi_cell(0, 8, txt=clean_for_pdf(content))
    
    path = "Sentinel_Full_Report.pdf"
    pdf.output(path)
    return send_file(path, as_attachment=True)

@app.route('/generate_quick_pdf', methods=['POST'])
def quick_pdf():
    data = request.json
    text = data.get('text', 'No Intelligence Data Provided')
    path = generate_quick_pdf(text)
    return send_file(path, as_attachment=True)





###################   genrate key properly and add somthing from here ##################








def sentinel_file_scanner(directory_path):
    patterns = {
        "Google API Key": r'AIza[0-9A-Za-z-_]{35}',
        "AWS Access Key": r'AKIA[0-9A-Z]{16}',
        "Hardcoded Password": r'(?i)password\s*=\s*["\'](.*?)["\']',
        "GitHub Token": r'ghp_[a-zA-Z0-9]{36}'
    }
    findings = []
    for root, dirs, files in os.walk(directory_path):
        if '.venv' in dirs:
            dirs.remove('.venv')
        for file in files:
            path = os.path.join(root, file)
            try:
                if file.endswith(('.py', '.env', '.txt', '.js')):
                    with open(path, 'r', errors='ignore') as f:
                        content = f.read()
                        for name, pattern in patterns.items():
                            if re.search(pattern, content):
                                findings.append(f"⚠️ {name} leak in {file}")
            except: 
                continue
    return findings


def perform_quantum_scan(target='127.0.0.1'):
    critical_gates = {21: "FTP", 22: "SSH", 80: "HTTP", 443: "HTTPS", 3389: "RDP"}
    active_threats = []
    for port, name in critical_gates.items():
        scanner = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        scanner.settimeout(0.01)
        try:
            if scanner.connect_ex((target, port)) == 0:
                active_threats.append(f"Port {port} ({name})")
        except:
            pass
        finally:
            scanner.close()
    return active_threats


def clean_for_pdf(raw_text):
    # Support multiple tag styles used across files and remove non-ascii
    clean = raw_text
    # Common tag variants
    for t in ['[H]', '[A]', '[S]', '[T]', '[[STRAT_INTEL]]', '[[CRIT_BREACH]]', '[[SEC_STABLE]]', '[[DATA_PACKET]]']:
        clean = clean.replace(t, '')
    return clean.encode('ascii', 'ignore').decode('ascii')


def generate_quick_pdf(text, path='quick_report.pdf'):
    pdf = FPDF()
    pdf.add_page()
    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(0, 150, 255)
    pdf.cell(0, 10, txt="SENTINEL TACTICAL INTELLIGENCE", ln=True, align='C')
    pdf.ln(10)

    lines = text.split('\n')
    for line in lines:
        if not line.strip():
            continue
        r, g, b = 0, 0, 0
        # detect both bracket styles
        if ('[H]' in line) or ('[[STRAT_INTEL]]' in line):
            r, g, b = 0, 150, 255
            pdf.set_font("Arial", 'B', 12)
        elif ('[A]' in line) or ('[[CRIT_BREACH]]' in line):
            r, g, b = 255, 15, 75
            pdf.set_font("Arial", 'B', 11)
        elif ('[S]' in line) or ('[[SEC_STABLE]]' in line):
            r, g, b = 0, 180, 60
        elif ('[T]' in line) or ('[[DATA_PACKET]]' in line):
            r, g, b = 150, 150, 0
        else:
            pdf.set_font("Arial", '', 11)

        safe_line = clean_for_pdf(line)
        pdf.set_text_color(r, g, b)
        pdf.multi_cell(0, 8, txt=safe_line)

    pdf.output(path)
    return path






























if __name__ == '__main__':
    app.run(debug=True, port=5002)




