from __future__ import annotations

from typing import TYPE_CHECKING

from odoo.tools import profiler

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from ..models.job import Job
    from ..models.session import Session

POPULATE_PROFILE_SESSION_KEY = 'populate_profile_session'


def get_profile_session_name(session: Session) -> str:
    """Return the stable populate label grouped under one profiler session."""
    return f"Populate Session {session.id}: {session.blueprint_id.name}"


def get_profile_description(job: Job) -> str:
    """Return the stable profiler label for one executable populate job."""
    ref = f" [{job.ref}]" if job.ref else ""
    return (
        f"populate session {job.session_id.id} | job {job.parent_path[:-1]} | "
        f"{job.model_name} {job.type}{ref}"
    )


def profiled_execution_scope(
    job: Job,
    profile_session: str,
    job_scope: AbstractContextManager[Job],
) -> AbstractContextManager[Job]:
    """Return ``job_scope`` wrapped with a profiler for executable jobs.

    Planner jobs are left unprofiled. Each executable job, including subjobs,
    gets its own ``ir.profile`` row.
    """
    if not job.is_executable:
        return job_scope

    job_profiler = profiler.Profiler(
        db=job.env.cr.dbname,
        description=get_profile_description(job),
        profile_session=profile_session,
    )
    return job_profiler._get_cm_proxy(job_scope)
