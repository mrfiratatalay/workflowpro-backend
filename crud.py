from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from models import Task, Project, User, TeamMember
from schemas import TaskCreate, TaskUpdate, ProjectCreate, ProjectUpdate, TeamMemberCreate
from typing import List, Optional

# Task CRUD operations
def get_tasks(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Task]:
    """Get all tasks for a specific user"""
    return db.query(Task).filter(Task.assigned_user_id == user_id).offset(skip).limit(limit).all()

def get_task(db: Session, task_id: int, user_id: int) -> Optional[Task]:
    """Get a specific task by ID for a user"""
    return db.query(Task).filter(and_(Task.id == task_id, Task.assigned_user_id == user_id)).first()

def create_task(db: Session, task: TaskCreate, user_id: int) -> Task:
    """Create a new task"""
    db_task = Task(
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        project_id=task.project_id,
        due_date=task.due_date,
        assigned_user_id=user_id
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def update_task(db: Session, task_id: int, task_update: TaskUpdate, user_id: int) -> Optional[Task]:
    """Update an existing task"""
    db_task = db.query(Task).filter(and_(Task.id == task_id, Task.assigned_user_id == user_id)).first()
    if not db_task:
        return None
    
    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_task, field, value)
    
    db.commit()
    db.refresh(db_task)
    return db_task

def delete_task(db: Session, task_id: int, user_id: int) -> bool:
    """Delete a task"""
    db_task = db.query(Task).filter(and_(Task.id == task_id, Task.assigned_user_id == user_id)).first()
    if not db_task:
        return False
    
    db.delete(db_task)
    db.commit()
    return True

# Project CRUD operations
def get_projects(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Project]:
    """Get all projects for a specific user (owned or team member)"""
    # Get projects owned by user or where user is a team member
    owned_projects = db.query(Project).filter(Project.owner_id == user_id)
    team_projects = db.query(Project).join(TeamMember).filter(TeamMember.user_id == user_id)
    return owned_projects.union(team_projects).offset(skip).limit(limit).all()

def get_project(db: Session, project_id: int, user_id: int) -> Optional[Project]:
    """Get a specific project by ID for a user"""
    # Check if user owns the project or is a team member
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return None
    
    # Check if user has access to this project
    if project.owner_id == user_id:
        return project
    
    team_member = db.query(TeamMember).filter(
        and_(TeamMember.project_id == project_id, TeamMember.user_id == user_id)
    ).first()
    
    return project if team_member else None

def create_project(db: Session, project: ProjectCreate, user_id: int) -> Project:
    """Create a new project"""
    db_project = Project(
        name=project.name,
        description=project.description,
        status=project.status,
        owner_id=user_id
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    # Add the owner as a team member with 'owner' role
    team_member = TeamMember(
        project_id=db_project.id,
        user_id=user_id,
        role="owner"
    )
    db.add(team_member)
    db.commit()
    
    return db_project

def update_project(db: Session, project_id: int, project_update: ProjectUpdate, user_id: int) -> Optional[Project]:
    """Update an existing project"""
    db_project = db.query(Project).filter(and_(Project.id == project_id, Project.owner_id == user_id)).first()
    if not db_project:
        return None
    
    update_data = project_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_project, field, value)
    
    db.commit()
    db.refresh(db_project)
    return db_project

def delete_project(db: Session, project_id: int, user_id: int) -> bool:
    """Delete a project"""
    db_project = db.query(Project).filter(and_(Project.id == project_id, Project.owner_id == user_id)).first()
    if not db_project:
        return False
    
    db.delete(db_project)
    db.commit()
    return True

def get_project_with_team(db: Session, project_id: int, user_id: int):
    """Get project with team members and task count"""
    project = get_project(db, project_id, user_id)
    if not project:
        return None
    
    # Load team members with user data
    team_members = db.query(TeamMember).filter(
        TeamMember.project_id == project_id
    ).all()
    
    # Count tasks in this project
    tasks_count = db.query(Task).filter(Task.project_id == project_id).count()
    
    return {
        **project.__dict__,
        "team_members": team_members,
        "tasks_count": tasks_count
    }

# Team Member CRUD operations
def add_team_member(db: Session, team_member: TeamMemberCreate, requester_user_id: int) -> Optional[TeamMember]:
    """Add a user to a project team"""
    # Check if requester is project owner or admin
    project = db.query(Project).filter(Project.id == team_member.project_id).first()
    if not project:
        return None
    
    if project.owner_id != requester_user_id:
        requester_membership = db.query(TeamMember).filter(
            and_(
                TeamMember.project_id == team_member.project_id,
                TeamMember.user_id == requester_user_id,
                TeamMember.role.in_(["owner", "admin"])
            )
        ).first()
        if not requester_membership:
            return None
    
    # Check if user is already a team member
    existing_member = db.query(TeamMember).filter(
        and_(
            TeamMember.project_id == team_member.project_id,
            TeamMember.user_id == team_member.user_id
        )
    ).first()
    
    if existing_member:
        return None  # User already in team
    
    db_team_member = TeamMember(**team_member.model_dump())
    db.add(db_team_member)
    db.commit()
    db.refresh(db_team_member)
    return db_team_member

def remove_team_member(db: Session, project_id: int, user_id: int, requester_user_id: int) -> bool:
    """Remove a user from a project team"""
    # Check if requester has permission
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return False
    
    if project.owner_id != requester_user_id:
        requester_membership = db.query(TeamMember).filter(
            and_(
                TeamMember.project_id == project_id,
                TeamMember.user_id == requester_user_id,
                TeamMember.role.in_(["owner", "admin"])
            )
        ).first()
        if not requester_membership:
            return False
    
    # Cannot remove project owner
    if project.owner_id == user_id:
        return False
    
    team_member = db.query(TeamMember).filter(
        and_(TeamMember.project_id == project_id, TeamMember.user_id == user_id)
    ).first()
    
    if team_member:
        db.delete(team_member)
        db.commit()
        return True
    
    return False

def get_team_members(db: Session, project_id: int, user_id: int) -> Optional[List[TeamMember]]:
    """Get all team members for a project"""
    # Check if user has access to the project
    project = get_project(db, project_id, user_id)
    if not project:
        return None
    
    return db.query(TeamMember).filter(TeamMember.project_id == project_id).all()

def search_users_by_email(db: Session, email_query: str, limit: int = 10) -> List[User]:
    """Search users by email for team invitations"""
    return db.query(User).filter(
        User.email.ilike(f"%{email_query}%")
    ).limit(limit).all()

# Reporting Functions
def get_system_overview(db: Session):
    """Get overall system statistics"""
    total_users = db.query(User).count()
    total_projects = db.query(Project).count()
    total_tasks = db.query(Task).count()
    completed_tasks = db.query(Task).filter(Task.status == "completed").count()
    active_tasks = db.query(Task).filter(Task.status.in_(["pending", "in_progress"])).count()
    
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    return {
        "total_users": total_users,
        "total_projects": total_projects,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "active_tasks": active_tasks,
        "completion_rate": round(completion_rate, 2)
    }

def get_user_task_statistics(db: Session):
    """Get task statistics for each user"""
    users = db.query(User).all()
    user_stats = []
    
    for user in users:
        total_tasks = db.query(Task).filter(Task.assigned_user_id == user.id).count()
        completed_tasks = db.query(Task).filter(
            and_(Task.assigned_user_id == user.id, Task.status == "completed")
        ).count()
        in_progress_tasks = db.query(Task).filter(
            and_(Task.assigned_user_id == user.id, Task.status == "in_progress")
        ).count()
        pending_tasks = db.query(Task).filter(
            and_(Task.assigned_user_id == user.id, Task.status == "pending")
        ).count()
        cancelled_tasks = db.query(Task).filter(
            and_(Task.assigned_user_id == user.id, Task.status == "cancelled")
        ).count()
        
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        user_stats.append({
            "user_id": user.id,
            "user_name": user.full_name or user.username,
            "user_email": user.email,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "in_progress_tasks": in_progress_tasks,
            "pending_tasks": pending_tasks,
            "cancelled_tasks": cancelled_tasks,
            "completion_rate": round(completion_rate, 2)
        })
    
    return user_stats

def get_project_task_statistics(db: Session):
    """Get task statistics for each project"""
    projects = db.query(Project).all()
    project_stats = []
    
    for project in projects:
        total_tasks = db.query(Task).filter(Task.project_id == project.id).count()
        completed_tasks = db.query(Task).filter(
            and_(Task.project_id == project.id, Task.status == "completed")
        ).count()
        in_progress_tasks = db.query(Task).filter(
            and_(Task.project_id == project.id, Task.status == "in_progress")
        ).count()
        pending_tasks = db.query(Task).filter(
            and_(Task.project_id == project.id, Task.status == "pending")
        ).count()
        cancelled_tasks = db.query(Task).filter(
            and_(Task.project_id == project.id, Task.status == "cancelled")
        ).count()
        
        team_size = db.query(TeamMember).filter(TeamMember.project_id == project.id).count()
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        project_stats.append({
            "project_id": project.id,
            "project_name": project.name,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "in_progress_tasks": in_progress_tasks,
            "pending_tasks": pending_tasks,
            "cancelled_tasks": cancelled_tasks,
            "completion_rate": round(completion_rate, 2),
            "team_size": team_size
        })
    
    return project_stats

def get_task_priority_distribution(db: Session):
    """Get distribution of tasks by priority"""
    priorities = ["low", "medium", "high", "urgent"]
    priority_stats = []
    
    for priority in priorities:
        count = db.query(Task).filter(Task.priority == priority).count()
        priority_stats.append({
            "priority": priority,
            "count": count
        })
    
    return priority_stats

def get_task_status_distribution(db: Session):
    """Get distribution of tasks by status"""
    statuses = ["pending", "in_progress", "completed", "cancelled"]
    status_stats = []
    
    for status in statuses:
        count = db.query(Task).filter(Task.status == status).count()
        status_stats.append({
            "status": status,
            "count": count
        })
    
    return status_stats

def get_recent_activity_count(db: Session, days: int = 7):
    """Get count of recent activity (tasks created/updated in last N days)"""
    from datetime import datetime, timedelta
    cutoff_date = datetime.now() - timedelta(days=days)
    
    recent_tasks = db.query(Task).filter(
        or_(
            Task.created_at >= cutoff_date,
            Task.updated_at >= cutoff_date
        )
    ).count()
    
    return recent_tasks

def generate_comprehensive_report(db: Session):
    """Generate a comprehensive report with all analytics"""
    return {
        "system_overview": get_system_overview(db),
        "user_stats": get_user_task_statistics(db),
        "project_stats": get_project_task_statistics(db),
        "task_priority_distribution": get_task_priority_distribution(db),
        "task_status_distribution": get_task_status_distribution(db),
        "recent_activity_count": get_recent_activity_count(db)
    }