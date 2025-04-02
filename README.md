## Overview
**LLM-AIOps** is an intelligent agent powered by AI, designed to simplify IT operations through **natural language commands**. Seamlessly integrated with LINE BOT, it enables users to manage **Proxmox VE (PVE)** and retrieve solutions from **API documentation** or **troubleshooting guides** using intelligent natural language processing and retrieval-augmented generation (RAG).

The system supports:
- **Executing API commands** to manage Proxmox VE infrastructure.
- **Searching troubleshooting or API guides** from a document database for complex issues.

## System Architecture
The system works as follows:
1. **Natural Language Input**: Users send queries or commands via **LINE BOT**.
2. **Webhook Handler**: FastAPI processes the LINE webhook and forwards the query to the AI engine.
3. **AI Engine**: The engine uses a **Retriever** to determine:
   - If the query requires calling **Proxmox VE API**.
   - Or if it requires retrieving **API usage** or **troubleshooting documentation**.
4. **Proxmox VE API Interaction**:
   - If API execution is required, the system generates API requests, sends them to Proxmox VE, and returns the results.
5. **Documentation Retrieval (RAG)**:
   - For complex queries, the **Retriever** searches a **Vector Database** built from documents (e.g., crawled data, Excel, PDF).
   - The AI responds with relevant solutions.
6. **Response Delivery**: The final response, including execution results or retrieved information, is sent back to the user via LINE BOT.

## Features
✅ **Natural Language Command Execution** – Convert user input into IT automation commands.  
✅ **LINE BOT Interaction** – Seamlessly communicate via chat to manage IT tasks.  
✅ **Proxmox VE Automation** – Manage VMs, monitor resources, and execute API requests automatically.  
✅ **Troubleshooting Assistance with RAG** – Retrieve relevant solutions from documentation for complex issues.  
✅ **FastAPI Webhook** – Process LINE events and handle backend operations.  

## Installation
```bash
git clone https://github.com/Yicheng-1218/LLM-AIOps.git
cd LLM-AIOps
pip install -r requirements.txt
```

## LINE BOT Setup
1. **Create a LINE BOT** on the [LINE Developers Console](https://developers.line.biz/).  
2. Obtain your **Channel Access Token** and **Channel Secret**.  
3. Set up the webhook to point to your FastAPI backend.  
4. Configure the environment variables in a `.env` file:
```env
LINE_CHANNEL_SECRET=your_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=your_access_token
```

## Run the LINE BOT Handler
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Set the LINE webhook URL to:  
📌 `https://your-server.com/callback`

## Usage Example

### 1️⃣ Sending Commands
Send a command in LINE chat, such as:
```
Create a new VM with 4 CPUs and 8GB RAM.
```
The system processes the request and returns the result.

### 2️⃣ Requesting Troubleshooting Assistance
If you need help with an error or API usage, ask:
```
How do I restart a VM in Proxmox VE?
```
The bot retrieves relevant documentation and provides a solution.

### 3️⃣ Forgetting Conversation History
To reset your session, send:
```
/forget
```

## API Endpoints

### LINE BOT Webhook
**Endpoint:**  
```http
POST /callback
```
Handles LINE BOT events and processes user queries.

### Retrieve Proxmox VE Screenshot
**Endpoint:**  
```http
GET /screenshot
```
Fetches the latest screenshot from Proxmox VE.

---

## Architecture Diagram
Below is the high-level architecture of **LLM-AIOps**:
![Architecture Diagram](https://github.com/user-attachments/assets/614ef65b-bddc-443c-9ef1-8533f65a77ca)

## License
This project is released under the MIT License. If you find it useful or would like to reference it in your work, attribution is appreciated!


