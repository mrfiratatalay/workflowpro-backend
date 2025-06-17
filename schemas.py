from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from models import TaskStatus, TaskPriority, ProjectStatus

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Project Schemas
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: Optional[ProjectStatus] = ProjectStatus.PLANNING

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None

class ProjectResponse(ProjectBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    owner: Optional[UserResponse] = None

    class Config:
        from_attributes = True

# Team Member Schemas
class TeamMemberBase(BaseModel):
    role: Optional[str] = "member"

class TeamMemberCreate(TeamMemberBase):
    user_id: int
    project_id: int

class TeamMemberResponse(TeamMemberBase):
    id: int
    project_id: int
    user_id: int
    joined_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True

class ProjectWithTeamResponse(ProjectResponse):
    team_members: List[TeamMemberResponse] = []
    tasks_count: Optional[int] = 0

    class Config:
        from_attributes = True

# Reporting Schemas
class UserTaskStats(BaseModel):
    user_id: int
    user_name: str
    user_email: str
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    pending_tasks: int
    cancelled_tasks: int
    completion_rate: float

class ProjectTaskStats(BaseModel):
    project_id: int
    project_name: str
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    pending_tasks: int
    cancelled_tasks: int
    completion_rate: float
    team_size: int

class TaskPriorityStats(BaseModel):
    priority: str
    count: int

class TaskStatusStats(BaseModel):
    status: str
    count: int

class SystemOverview(BaseModel):
    total_users: int
    total_projects: int
    total_tasks: int
    completed_tasks: int
    active_tasks: int
    completion_rate: float

class ReportsResponse(BaseModel):
    system_overview: SystemOverview
    user_stats: List[UserTaskStats]
    project_stats: List[ProjectTaskStats]
    task_priority_distribution: List[TaskPriorityStats]
    task_status_distribution: List[TaskStatusStats]
    recent_activity_count: int

# Task Schemas
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[TaskStatus] = TaskStatus.PENDING
    priority: Optional[TaskPriority] = TaskPriority.MEDIUM
    project_id: Optional[int] = None
    due_date: Optional[datetime] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    project_id: Optional[int] = None
    due_date: Optional[datetime] = None

class TaskResponse(TaskBase):
    id: int
    assigned_user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    assigned_user: Optional[UserResponse] = None
    project: Optional[ProjectResponse] = None

    class Config:
        from_attributes = True 