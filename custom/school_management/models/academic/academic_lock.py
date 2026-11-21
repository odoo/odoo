def can_maintain_closed_year_records(env):
    """Return whether this request has the explicit closed-year maintenance grant."""
    if not env.context.get("allow_closed_year_write"):
        return False
    return (
        env.is_superuser()
        or env.user.has_group("school_management.group_academic_year_manager")
        or env.user.has_group("school_management.group_school_admin")
    )
