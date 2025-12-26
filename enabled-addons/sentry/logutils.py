# Copyright 2016-2017 Versada <https://versada.eu/>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import os.path
import urllib.parse

from werkzeug import datastructures

from .generalutils import get_environ
from .processor import SanitizePasswordsProcessor


def get_request_info(request):
    """
    Returns context data extracted from :param:`request`.

    Heavily based on flask integration for Sentry: https://git.io/vP4i9.
    """
    urlparts = urllib.parse.urlsplit(request.url)
    return {
        "url": f"{urlparts.scheme}://{urlparts.netloc}{urlparts.path}",
        "query_string": urlparts.query,
        "method": request.method,
        "headers": dict(datastructures.EnvironHeaders(request.environ)),
        "env": dict(get_environ(request.environ)),
    }


def get_extra_context(request):
    """
    Extracts additional context from the current request (if such is set).
    """
    try:
        session = getattr(request, "session", {})
    except RuntimeError:
        ctx = {}
    else:
        ctx = {
            "tags": {
                "database": session.get("db", None),
            },
            "user": {
                "email": session.get("login", None),
                "id": session.get("uid", None),
            },
            "extra": {
                "context": session.get("context", {}),
            },
        }
        if request.httprequest:
            ctx.update({"request": get_request_info(request.httprequest)})
    return ctx


class SanitizeOdooCookiesProcessor(SanitizePasswordsProcessor):
    """Custom :class:`raven.processors.Processor`.
    Allows to sanitize sensitive Odoo cookies, namely the "session_id" cookie.
    """

    KEYS = frozenset(
        [
            "session_id",
        ]
    )


class InvalidGitRepository(Exception):
    pass


def fetch_git_sha(path, head=None):
    """>>> fetch_git_sha(os.path.dirname(__file__))
    Taken from https://git.io/JITmC
    """
    if not head:
        head_path = os.path.join(path, ".git", "HEAD")
        if not os.path.exists(head_path):
            raise InvalidGitRepository(
                f"Cannot identify HEAD for git repository at {path}"
            )

        with open(head_path) as fp:
            head = str(fp.read()).strip()

        if head.startswith("ref: "):
            head = head[5:]
            revision_file = os.path.join(path, ".git", *head.split("/"))
        else:
            return head
    else:
        revision_file = os.path.join(path, ".git", "refs", "heads", head)

    if not os.path.exists(revision_file):
        if not os.path.exists(os.path.join(path, ".git")):
            raise InvalidGitRepository(
                f"{path} does not seem to be the root of a git repository"
            )

        # Check for our .git/packed-refs' file since a `git gc` may have run
        # https://git-scm.com/book/en/v2/Git-Internals-Maintenance-and-Data-Recovery
        packed_file = os.path.join(path, ".git", "packed-refs")
        if os.path.exists(packed_file):
            with open(packed_file) as fh:
                for line in fh:
                    line = line.rstrip()
                    if line and line[:1] not in ("#", "^"):
                        try:
                            revision, ref = line.split(" ", 1)
                        except ValueError:
                            continue
                        if ref == head:
                            return str(revision)

        raise InvalidGitRepository(f"Unable to find ref to head {head} in repository")

    with open(revision_file) as fh:
        return str(fh.read()).strip()
