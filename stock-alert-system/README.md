
# 📈 Stock Alert Telegram System

## 📦 Components
- Flask API for sending Telegram alerts
- Streamlit app for managing users and alerts

## 🚀 Deployment

### Backend on Render
- Deploy from `/backend` directory Dockerfile
- Set TELEGRAM_BOT_TOKEN env var

### Frontend on Streamlit Cloud
- App entry point: `/frontend/streamlit_app.py`
- Edit BACKEND_URL to match your Render backend URL

## 📦 Local Dev

```bash
docker-compose up --build
```

- Backend: http://localhost:5000
- Frontend: http://localhost:8501
