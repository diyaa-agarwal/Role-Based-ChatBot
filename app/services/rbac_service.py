ROLE_PERMISSIONS = {
    "finance": ["finance", "general"],
    "marketing": ["marketing", "general"],
    "hr": ["hr", "general"],
    "engineering": ["engineering", "general"],
    "employee": ["general"],
    "c_level": ["finance", "marketing", "hr", "engineering", "general"]
}

def get_allowed_departments(role):
    return ROLE_PERMISSIONS.get(role, [])

def is_department_allowed(role, department):
    allowed_departments = get_allowed_departments(role)
    return department in allowed_departments

