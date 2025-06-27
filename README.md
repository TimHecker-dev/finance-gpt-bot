## Configuration and Security Notice

**IMPORTANT:**  
This project uses external API keys, which must be stored in the file `config.txt`.


1. Copy the file `config.example.txt` to `config.txt`.
2. Enter your personal API keys and endpoints into `config.txt`.
3. **Attention:** Make sure that `config.txt` is listed in your `.gitignore` file and is never added to the public repository!
4. Never share your API keys publicly.

## Installation

Before running the application, install all required dependencies with:

```bash
pip install -r requirements_chatbot.txt
```

**How to Run the Application**
You can start the Finance Chatbot using the following command in your terminal (adjust the path if necessary):

`streamlit run c:\users\folder\finanz_chatbot.py`
Replace the path with the actual location of your Python file if it differs.

Example of a `config.txt`:

```ini
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_API_ENDPOINT=your_endpoint
OPENAI_API_VERSION=your_version
NEWSAPI_KEY=your_newsapi_key
OPENEXCHANGE_API_KEY=your_openexchange_key
```
