from flask import Flask, render_template, request
import anthropic
import pypdf
import docx
import os
import json

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
    summary = None
    key_terms = None
    timeline_label = None
    timeline_items = None
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
                prompt = f"""The following text was extracted from a document or PDF and may contain some garbled or disjointed fragments (for example, from charts, graphs, or tables). Ignore any fragments that don't form coherent sentences, and base your analysis only on the clear, readable prose.

Analyze the following text for a student studying it. Respond ONLY with a valid JSON object, no other text before or after, with these exact keys:
- "summary": a clear, simplified summary of the main content in plain language
- "key_terms": an array of objects, each with "term" and "meaning" keys, covering the most important terms in the text (empty array if none apply)
- "timeline_type": either "timeline" if the text has a clear chronological sequence of events, or "context" if it does not
- "timeline_items": an array of short strings. If timeline_type is "timeline", each item should be a date/event. If timeline_type is "context", each item should be an important contextual point to know (3-5 items).

Text:
{content}"""

                message = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=1500,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )

                raw_response = message.content[0].text.strip()

                if raw_response.startswith("```"):
                    raw_response = raw_response.split("```")[1]
                    if raw_response.startswith("json"):
                        raw_response = raw_response[4:]
                    raw_response = raw_response.strip()

                parsed = json.loads(raw_response)

                summary = parsed.get("summary")
                key_terms = parsed.get("key_terms", [])
                timeline_label = "Timeline" if parsed.get("timeline_type") == "timeline" else "Important Context"
                timeline_items = parsed.get("timeline_items", [])

            except json.JSONDecodeError:
                error = "The response couldn't be processed. Please try again."
            except Exception as e:
                error = f"Something went wrong: {str(e)}"

    return render_template(
        'index.html',
        summary=summary,
        key_terms=key_terms,
        timeline_label=timeline_label,
        timeline_items=timeline_items,
        error=error
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)