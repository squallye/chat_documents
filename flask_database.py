from flask import Flask, render_template, request, redirect, url_for,session,flash,jsonify
from database import engine
from sqlalchemy import text
import json
from PyPDF2 import PdfReader
import os
from dotenv import load_dotenv
import shutil
import chromadb
import uuid

from langchain.text_splitter import CharacterTextSplitter
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddings,
)

load_dotenv()



OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY


app = Flask(__name__)
app.secret_key = 'your_secret_key'
llm= ChatOpenAI(temperature=0)
persist_directory = 'db'
#embeddings = OpenAIEmbeddings()
embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="chroma_db")

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER




def load_users_from_db():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM users"))
        result_dicts = []
        for row in result.fetchall():
            user_dict = dict(row._mapping.items())
            result_dicts.append(user_dict)
        return result_dicts


# def extract_text_from_pdf(file):
#     """
#     Extracts text from a PDF file using PyPDF2.
#     """
#     pdf_reader = PdfReader(file)
#     text_content = ''
#     for page_num in range(len(pdf_reader.pages)):
#         text_content += pdf_reader.pages[page_num].extract_text()
#     return text_content

# def get_text_chunks(text):
#     text_splitter = RecursiveCharacterTextSplitter(
        
#         chunk_size=1000,
#         chunk_overlap=200,
#         length_function=len
#     )
#     chunks = text_splitter.split_documents(text)
#     return chunks

def clear_uploads():
    # Clear the contents of the upload folder
    shutil.rmtree(app.config['UPLOAD_FOLDER'])
    os.makedirs(app.config['UPLOAD_FOLDER'])
    return 'Upload folder cleared successfully'


@app.route('/')
def index():
    message = request.args.get('message', '')  # Get the message from the query parameters
    return render_template('index.html', message=message)

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/register_user', methods=['POST'])
def register_user():
    username = request.form.get('username')
    password = request.form.get('password')
    email = request.form.get('email')

    with engine.connect() as conn:
        conn.execute(text("INSERT INTO users (username, password, email) VALUES (:username, :password, :email)"),
                     {'username': username, 'password': password, 'email': email})
        conn.execute(text('''UPDATE users SET knowledgebase = '{"kb1": "Default collection"}' '''))



    message = "Registration completed successfully!"
    return redirect(url_for('index', message=message))

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login_user', methods=['POST'])
def login_user():
    username = request.form.get('username')
    password = request.form.get('password')

    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM users WHERE username = :username"), {'username': username})
        user = result.fetchone()

        if user is None:
            message = "Username doesn't exist"
            return render_template('login.html', message=message)

        if user.password == password:
            # Redirect to the knowledgebase page upon successful login
            session['user'] = {'username': user.username}
            return redirect(url_for('knowledgebase'))
        else:
            message = "Wrong password"
            return render_template('login.html', message=message)

@app.route('/knowledgebase')
def knowledgebase():
    user = session.get('user', None)

    if user is None:
        # Redirect to login if the user is not in session (not logged in)
        return redirect(url_for('login'))
    
    

    # Fetch the knowledgebase data from the database
    with engine.connect() as conn:
        result = conn.execute(text("SELECT knowledgebase FROM users WHERE username = :username"),
                              {'username': user['username']})
        knowledgebase_data_str = result.scalar()  # Assuming it returns a single scalar value (JSON data as a string)

    # Parse the knowledgebase data as JSON
    try:
        knowledgebase_data = json.loads(knowledgebase_data_str)
    except (json.JSONDecodeError, TypeError):
        knowledgebase_data = {}

    return render_template('knowledgebase.html', user=user, knowledgebase_data=knowledgebase_data,
                           )



@app.route('/update_knowledgebase', methods=['POST'])
def update_knowledgebase():
    # Get the user information from the session
    user = session.get('user', None)

    if user is None:
        # Redirect to login if the user is not in the session (not logged in)
        return redirect(url_for('login'))

    key = request.form.get('key')
    value = request.form.get('value')


    
    # Update the 'knowledgebase' column in the database with the new record
    with engine.connect() as conn:
              
        conn.execute(text("UPDATE users SET knowledgebase = JSON_SET(knowledgebase, :key_path, :value) WHERE username = :username"),
                     {'username': user['username'], 'key_path': f'$.{key}', 'value': value})

        
        

    # Redirect back to the knowledgebase page after adding the record
    return redirect(url_for('knowledgebase'))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part'
    
    file = request.files['file']
    
    if file.filename == '':
        return 'No selected file'
    
    if file:
        # Save the file to the upload folder
   
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        flash(f'File "{file.filename}" uploaded successfully', 'success')

        return redirect(url_for('knowledgebase'))

@app.route('/process_pdf', methods=['POST'])
def process_pdf():
    # Get the user information from the session
    user = session.get('user', None)

    if user is None:
        # Redirect to login if the user is not in the session (not logged in)
        return redirect(url_for('login'))

    key = request.form.get('selected_record')
    
    if key:
        loader = DirectoryLoader('./uploads/', glob="./*.pdf",show_progress=True)
        documents = loader.load()

        #splitting the text into
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        docs = text_splitter.split_documents(documents)

        # Create a dynamic collection name based on username and selected record
        collection_name = f"{user['username']}_{key}"
        collection = client.get_or_create_collection(collection_name)
        for doc in docs:
            collection.add(
                ids=[str(uuid.uuid1())], metadatas=doc.metadata, documents=doc.page_content
            )

        clear_uploads()

        # with engine.connect() as conn:
        #     conn.execute(text("UPDATE users SET document_text = JSON_REPLACE(document_text, :key_path, :value) WHERE username = :username"),
        #                 {'username': user['username'], 'key_path': f'$.{key}', 'value': pdf_text})    
              
        

    # Redirect back to the knowledgebase page after adding the record
    return redirect(url_for('knowledgebase'))


@app.route('/chat_document', methods=['POST'])
def chat_document():
    user = session.get('user', None)
    # Get the selected document text key
    selected_document_text_key = request.form.get('selected_document_text_key', None)

    # Fetch the selected document text based on the selected key
    if selected_document_text_key:

        collection_name = f"{user['username']}_{selected_document_text_key}"


        vectordb = Chroma(
            client=client,
            collection_name=collection_name,
            embedding_function=embeddings,
        )
        
        retriever = vectordb.as_retriever()

        qa_chain = RetrievalQA.from_chain_type(llm=llm, 
                                  chain_type="stuff", 
                                  retriever=retriever, 
                                  return_source_documents=False)
 

        user_query = request.form.get('user_query', '')
        result = qa_chain(user_query)

        return jsonify({'answer': result})
    
if __name__ == '__main__':
    app.run(debug=True)
