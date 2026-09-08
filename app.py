from flask import Flask, render_template, request
import anthropic
import pypdf
import docx
import os

app = Flask(__name__)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def extract_text(file):
    filename = file.filename.lower()

    if filename.endswith('.txt'):
        return file.read().decode('utf-8')

    elif filename.endswith('.pdf'):
        reader = pypdf.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text

    elif filename.endswith('.docx'):
        document = docx.Document(file)
        text = "\n".join([para.text for para in document.paragraphs])
        return text

    else:
        return None

@app.route('/', methods=['GET', 'POST'])
def home():
    result = None
    error = None

    if request.method == 'POST':
        text_input = request.form.get('text_input', '').strip()
        uploaded_file = request.files.get('file_input')

        content = None

        if uploaded_file and uploaded_file.filename != '':
            content = extract_text(uploaded_file)
            if content is None:
                error = "Unsupported file type. Please upload a .txt, .pdf, or .docx file."
        elif text_input:
            content = text_input
        else:
            error = "Please paste some text or upload a file."

        if content:
            try:
                message = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=1000,
                    messages=[
                        {
                            "role": "user",
                            "content": f"Simplify and summarize the following text in plain, easy to understand language:\n\n{content}"
                        }
                    ]
                )
                result = message.content[0].text
            except Exception as e:
                error = f"Something went wrong: {str(e)}"

    return render_template('index.html', result=result, error=error)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)