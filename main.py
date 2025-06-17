from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from database import get_db, engine, SQLALCHEMY_DATABASE_URL
from models import Base, User, Task, Project
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from schemas import (
    UserCreate, UserLogin, UserResponse, Token,
    TaskCreate, TaskUpdate, TaskResponse,
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectWithTeamResponse,
    TeamMemberCreate, TeamMemberResponse, ReportsResponse
)
from auth import get_password_hash, verify_password, create_access_token, get_current_user
import crud

# Log database configuration
if SQLALCHEMY_DATABASE_URL.startswith("mysql"):
    logger.info("🗄️  Using MySQL database (Railway)")
    logger.info(f"🔗 Database host: {SQLALCHEMY_DATABASE_URL.split('@')[1].split(':')[0]}")
else:
    logger.info("🗄️  Using SQLite database (Local)")

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created/updated successfully")
except Exception as e:
    logger.error(f"❌ Database initialization error: {e}")
    logger.info("⚠️  Application will continue, but database operations may fail")

app = FastAPI(title="WorkFlowPro API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/ping")
async def ping():
    return {"message": "pong", "status": "healthy"}

@app.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@app.post("/login", response_model=Token)
async def login_user(user: UserLogin, db: Session = Depends(get_db)):
    # Find user by email
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if user is active
    if not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

# Task Management Endpoints
@app.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all tasks for the current user"""
    return crud.get_tasks(db, current_user.id, skip, limit)

@app.post("/tasks", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new task"""
    return crud.create_task(db, task, current_user.id)

@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific task by ID"""
    task = crud.get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing task"""
    task = crud.update_task(db, task_id, task_update, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a task"""
    success = crud.delete_task(db, task_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}

# Project Management Endpoints
@app.get("/projects", response_model=List[ProjectResponse])
async def get_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all projects for the current user"""
    return crud.get_projects(db, current_user.id, skip, limit)

@app.post("/projects", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new project"""
    return crud.create_project(db, project, current_user.id)

@app.get("/projects/{project_id}", response_model=ProjectWithTeamResponse)
async def get_project_detail(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed project information with team members"""
    project_data = crud.get_project_with_team(db, project_id, current_user.id)
    if not project_data:
        raise HTTPException(status_code=404, detail="Project not found")
    return project_data

# Team Management Endpoints
@app.post("/projects/{project_id}/team", response_model=TeamMemberResponse)
async def add_team_member(
    project_id: int,
    team_member_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a user to a project team"""
    team_member = TeamMemberCreate(
        project_id=project_id,
        user_id=team_member_data["user_id"],
        role=team_member_data.get("role", "member")
    )
    
    result = crud.add_team_member(db, team_member, current_user.id)
    if not result:
        raise HTTPException(
            status_code=400,
            detail="Cannot add team member. User may already be in the team or you don't have permission."
        )
    return result

@app.delete("/projects/{project_id}/team/{user_id}")
async def remove_team_member(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a user from a project team"""
    success = crud.remove_team_member(db, project_id, user_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove team member. User may not exist or you don't have permission."
        )
    return {"message": "Team member removed successfully"}

@app.get("/projects/{project_id}/team", response_model=List[TeamMemberResponse])
async def get_team_members(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all team members for a project"""
    team_members = crud.get_team_members(db, project_id, current_user.id)
    if team_members is None:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    return team_members

@app.get("/users/search")
async def search_users(
    email: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search users by email for team invitations"""
    if len(email) < 3:
        raise HTTPException(status_code=400, detail="Search query must be at least 3 characters")
    
    users = crud.search_users_by_email(db, email)
    return [{"id": user.id, "email": user.email, "full_name": user.full_name} for user in users]

# Reporting Endpoints
@app.get("/reports", response_model=ReportsResponse)
async def get_comprehensive_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive analytics and reporting data"""
    # For now, allow all authenticated users to view reports
    # In production, you might want to add admin-only access control
    try:
        report_data = crud.generate_comprehensive_report(db)
        return report_data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating reports: {str(e)}"
        )

@app.get("/reports/system-overview")
async def get_system_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get system overview statistics"""
    return crud.get_system_overview(db)

@app.get("/reports/user-stats")
async def get_user_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get task statistics for all users"""
    return crud.get_user_task_statistics(db)

@app.get("/reports/project-stats")
async def get_project_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get task statistics for all projects"""
    return crud.get_project_task_statistics(db)

@app.get("/reports/priority-distribution")
async def get_priority_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get task distribution by priority"""
    return crud.get_task_priority_distribution(db)

@app.get("/reports/status-distribution")
async def get_status_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get task distribution by status"""
    return crud.get_task_status_distribution(db)