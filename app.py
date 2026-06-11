import os
from flask import Flask, render_template, request, jsonify
from pypdf import PdfReader
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super-secret-dev-key")

hf_token = os.getenv("HF_TOKEN")
client = InferenceClient(model="Qwen/Qwen2.5-7B-Instruct", token=hf_token)

PAPER_STORAGE = {
    "text": ""
}

def extract_text_from_pdf(pdf_file):
    pdf_reader = PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

@app.route('/')
def home():
    PAPER_STORAGE["text"] = ""  # Clear memory on refresh
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        text = extract_text_from_pdf(file)
        
        PAPER_STORAGE["text"] = text[:16000]  
        
        messages = [
            {
                "role": "system", 
                "content": (
                    "You are an expert research assistant. Provide a concise, structured markdown summary "
                    "of the research paper provided. Break it down explicitly into these four parts:\n"
                    "1. Main Objective\n2. Methodology\n3. Key Findings/Contributions\n4. Limitations\n"
                    "Use professional tone and clean bullet points."
                )
            },
            {"role": "user", "content": f"Paper Content:\n{PAPER_STORAGE['text']}"}
        ]
        
        response = client.chat_completion(
            messages=messages,
            max_tokens=600,
            temperature=0.2
        )
        summary = response.choices[0].message.content
        return jsonify({"summary": summary})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    paper_text = PAPER_STORAGE.get("text")  # 🚀 Pull straight from server memory
    
    if not paper_text:
        return jsonify({"error": "Please upload and process a paper first."}), 400
    
    try:
        messages = [
            {
                "role": "system", 
                "content": (
                    "You are an expert technical assistant. Answer the user's question accurately, "
                    "relying directly on the provided research paper context. If it cannot be answered "
                    "using the text, say so clearly."
                )
            },
            {"role": "user", "content": f"Context:\n{paper_text}\n\nQuestion: {user_message}"}
        ]
        
        response = client.chat_completion(
            messages=messages,
            max_tokens=400,
            temperature=0.25
        )
        reply = response.choices[0].message.content
        return jsonify({"reply": reply})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)