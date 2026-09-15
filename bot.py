# bot.py
import os
import logging
import tempfile
import fitz  # PyMuPDF
from docx import Document
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from extractor import TenderExtractor

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 **FOREX EXPERT TRADER BOT**\n\n"
        "I extract key data from your documents.\n"
        "Send me a **PDF** or **DOCX** file and I will reply with:\n"
        "• Requirements\n"
        "• Submission deadline\n"
        "• Required documents\n"
        "• Eligibility criteria\n"
        "• Evaluation criteria\n"
        "• Budget information\n"
        "• Important clauses",
        parse_mode='Markdown'
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    doc = message.document
    
    # Validate file type
    allowed_extensions = ['.pdf', '.docx', '.txt']
    file_name = doc.file_name
    ext = os.path.splitext(file_name)[1].lower()
    
    if ext not in allowed_extensions:
        await message.reply_text("❌ Please send a PDF, DOCX, or TXT file.")
        return

    await message.reply_text(f"📄 Processing `{file_name}`... Please wait.", parse_mode='Markdown')

    try:
        # Download file to temp location
        file = await context.bot.get_file(doc.file_id)
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            await file.download_to_drive(tmp.name)
            tmp_path = tmp.name

        # Extract text based on file type
        text = ""
        if ext == '.pdf':
            with fitz.open(tmp_path) as pdf_doc:
                text = "\n".join([page.get_text() for page in pdf_doc])
        elif ext == '.docx':
            docx_doc = Document(tmp_path)
            text = "\n".join([para.text for para in docx_doc.paragraphs])
        elif ext == '.txt':
            with open(tmp_path, 'r', encoding='utf-8') as f:
                text = f.read()

        # Cleanup temp file
        os.unlink(tmp_path)

        if not text.strip():
            await message.reply_text("❌ Could not extract text. The file might be scanned or empty.")
            return

        # Run extraction
        extractor = TenderExtractor(text)
        data = extractor.extract_all()

        # Format response
        response = _format_response(data)
        
        # Telegram has a 4096 char limit; split if necessary
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await message.reply_text(response[i:i+4000])
        else:
            await message.reply_text(response, parse_mode='Markdown')

    except Exception as e:
        logging.error(f"Error processing document: {e}")
        await message.reply_text("❌ An error occurred while processing the document.")

def _format_response(data) -> str:
    """Helper to format ExtractedData into a readable string."""
    sections = [
        ("📋 **Requirements**", data.requirements),
        ("📅 **Submission Deadline**", data.submission_deadline),
        ("📁 **Required Documents**", data.required_documents),
        ("✅ **Eligibility Criteria**", data.eligibility_criteria),
        ("📊 **Evaluation Criteria**", data.evaluation_criteria),
        ("💰 **Budget Information**", data.budget_information),
        ("⚠️ **Important Clauses**", data.important_clauses)
    ]
    
    output = "**📑 EXTRACTION RESULTS**\n\n"
    for title, content in sections:
        output += f"{title}\n"
        if isinstance(content, list):
            if content:
                for item in content:
                    output += f"• {item}\n"
            else:
                output += "• Not found\n"
        else:
            output += f"{content}\n"
        output += "\n"
    
    return output

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set.")
    
    application = Application.builder().token(token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # For Railway (Polling mode is fine as a long-running worker)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
