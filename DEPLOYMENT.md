# WorkflowPro Backend - Railway Deployment Guide

## 🚀 Quick Deploy to Railway

### 1. Connect Your Repository

- Go to [Railway](https://railway.app)
- Click "New Project" → "Deploy from GitHub repo"
- Select your `workflowpro` repository
- Choose the `workflowpro-backend` folder as the root directory

### 2. Environment Variables Setup

In Railway's "Variables" tab, add these environment variables:

```
DATABASE_URL=mysql://username:password@host:port/database_name
JWT_SECRET_KEY=your-super-secret-jwt-key-here-make-it-long-and-random
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 3. Database Setup

- Add a MySQL database service in Railway
- Copy the DATABASE_URL from Railway's database service
- Paste it into your environment variables

### 4. Deploy

- Railway will automatically detect your FastAPI app
- It will install dependencies from `requirements.txt`
- Your API will be available at: `https://your-app-name.railway.app`

## 🔍 API Endpoints

Once deployed, you can access:

- **Swagger UI**: `https://your-app-name.railway.app/docs`
- **Health Check**: `https://your-app-name.railway.app/ping`
- **API Root**: `https://your-app-name.railway.app/`

## 🛠️ Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 📋 Checklist Before Deploy

- ✅ `main.py` contains `app = FastAPI()`
- ✅ `requirements.txt` includes all dependencies
- ✅ Environment variables use `os.getenv()`
- ✅ Database URL is configurable via environment
- ✅ CORS is configured for your frontend domain
