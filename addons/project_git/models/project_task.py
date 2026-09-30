import html
import json
import os
import re
import subprocess
from collections import defaultdict

from odoo import _, fields, models
from odoo.exceptions import UserError


HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")
DIFF_GIT_RE = re.compile(r"^diff --git a/(.*?) b/(.*)$")
TAG_RE = re.compile(r"<[^>]+>")


class ProjectTask(models.Model):
    _inherit = "project.task"

    git_source_remote = fields.Char(string="Source Remote", default="origin")
    git_source_branch = fields.Char(string="Source Branch")
    git_target_remote = fields.Char(string="Target Remote")
    git_target_branch = fields.Char(string="Target Branch")
    git_repo_root = fields.Char(string="Git Repository Root", compute="_compute_git_environment")
    git_available_remotes = fields.Text(
        string="Available Remotes",
        compute="_compute_git_environment",
    )

    git_last_refresh = fields.Datetime(string="Last Diff Refresh", readonly=True)
    git_refresh_error = fields.Text(string="Last Diff Error", readonly=True)
    git_diff_raw = fields.Text(string="Raw Diff", readonly=True)
    git_diff_payload = fields.Text(string="Diff Payload", readonly=True)

    git_comment_file_path = fields.Char(string="Selected File", copy=False)
    git_comment_old_line = fields.Integer(string="Selected Old Line", copy=False)
    git_comment_new_line = fields.Integer(string="Selected New Line", copy=False)
    git_comment_side = fields.Selection(
        [("old", "Old"), ("new", "New")],
        string="Selected Side",
        default="new",
        copy=False,
    )
    git_comment_hunk_header = fields.Char(string="Selected Hunk", copy=False)
    git_comment_body = fields.Text(string="Inline Comment", copy=False)

    def _git_run(self, args, cwd):
        completed = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode:
            raise UserError(
                _(
                    "Git command failed:\n%(cmd)s\n\nstdout:\n%(stdout)s\n\nstderr:\n%(stderr)s"
                )
                % {
                    "cmd": " ".join(args),
                    "stdout": completed.stdout or "",
                    "stderr": completed.stderr or "",
                }
            )
        return (completed.stdout or "").strip()

    def _get_git_repo_root(self):
        cwd = os.getcwd()
        try:
            return self._git_run(["git", "rev-parse", "--show-toplevel"], cwd)
        except Exception:
            return False

    def _get_git_remote_names(self, repo_root=None):
        repo_root = repo_root or self._get_git_repo_root()
        if not repo_root:
            return []
        output = self._git_run(["git", "remote"], repo_root)
        return [line.strip() for line in output.splitlines() if line.strip()]

    def _compute_git_environment(self):
        repo_root = self._get_git_repo_root()
        remotes = []
        if repo_root:
            try:
                remotes = self._get_git_remote_names(repo_root)
            except Exception:
                remotes = []
        for task in self:
            task.git_repo_root = repo_root or False
            task.git_available_remotes = ", ".join(remotes) if remotes else False

    def _validate_git_compare_input(self):
        self.ensure_one()
        if not self.git_source_remote or not self.git_source_branch:
            raise UserError(_("Please set Source Remote and Source Branch."))
        if not self.git_target_branch:
            raise UserError(_("Please set Target Branch."))

        repo_root = self._get_git_repo_root()
        if not repo_root:
            raise UserError(
                _(
                    "The current Odoo working directory is not inside a git repository. "
                    "Start Odoo from a git checkout or adapt the module to point to a repository path."
                )
            )

        remotes = self._get_git_remote_names(repo_root)
        if not remotes:
            raise UserError(_("No git remotes were found in the current repository."))

        target_remote = self.git_target_remote or self.git_source_remote
        missing = [name for name in [self.git_source_remote, target_remote] if name not in remotes]
        if missing:
            raise UserError(
                _("Unknown git remote(s): %(names)s. Available remotes: %(remotes)s")
                % {
                    "names": ", ".join(missing),
                    "remotes": ", ".join(remotes),
                }
            )
        return repo_root, target_remote

    def _git_get_compare_info(self):
        self.ensure_one()
        repo_root, target_remote = self._validate_git_compare_input()

        source_ref = "refs/remotes/%s/%s" % (self.git_source_remote, self.git_source_branch)
        target_ref = "refs/remotes/%s/%s" % (target_remote, self.git_target_branch)

        try:
            head_sha = self._git_run(["git", "rev-parse", source_ref], repo_root)
        except Exception:
            raise UserError(
                _(
                    "Local remote-tracking ref not found: %(ref)s\n\n"
                    "This module reads existing refs only and does not fetch from Odoo. "
                    "Fetch that branch manually in the repository first, for example:\n"
                    "git fetch %(remote)s %(branch)s"
                )
                % {
                    "ref": source_ref,
                    "remote": self.git_source_remote,
                    "branch": self.git_source_branch,
                }
            )

        try:
            target_sha = self._git_run(["git", "rev-parse", target_ref], repo_root)
        except Exception:
            raise UserError(
                _(
                    "Local remote-tracking ref not found: %(ref)s\n\n"
                    "This module reads existing refs only and does not fetch from Odoo. "
                    "Fetch that branch manually in the repository first, for example:\n"
                    "git fetch %(remote)s %(branch)s"
                )
                % {
                    "ref": target_ref,
                    "remote": target_remote,
                    "branch": self.git_target_branch,
                }
            )

        raw_diff = self._git_run(
            [
                "git",
                "-c",
                "core.packedGitWindowSize=16m",
                "-c",
                "core.packedGitLimit=128m",
                "diff",
                "--no-color",
                "--no-ext-diff",
                "--find-renames",
                "--unified=3",
                "--merge-base",
                target_ref,
                source_ref,
            ],
            repo_root,
        )
        return {
            "base_sha": target_sha,
            "head_sha": head_sha,
            "raw_diff": raw_diff,
            "repo_root": repo_root,
            "source_ref": source_ref,
            "target_ref": target_ref,
        }

    def _message_body_to_text(self, body):
        text = TAG_RE.sub("", body or "")
        return html.unescape(text).strip()

    def _parse_unified_diff(self, raw_diff):
        files = []
        current_file = None
        current_hunk = None
        old_line = 0
        new_line = 0

        for raw_line in (raw_diff or "").splitlines():
            diff_git_match = DIFF_GIT_RE.match(raw_line)
            if diff_git_match:
                old_path = diff_git_match.group(1)
                new_path = diff_git_match.group(2)
                file_path = new_path if new_path != "/dev/null" else old_path
                current_file = {
                    "old_path": old_path,
                    "new_path": new_path,
                    "file_path": file_path,
                    "display_path": file_path,
                    "headers": [raw_line],
                    "hunks": [],
                }
                files.append(current_file)
                current_hunk = None
                continue

            if current_file is None:
                continue

            if raw_line.startswith(
                (
                    "index ",
                    "--- ",
                    "+++ ",
                    "new file mode ",
                    "deleted file mode ",
                    "similarity index ",
                    "rename from ",
                    "rename to ",
                )
            ):
                current_file["headers"].append(raw_line)
                if raw_line.startswith("+++ b/"):
                    current_file["display_path"] = raw_line[len("+++ b/") :].strip()
                    current_file["file_path"] = current_file["display_path"]
                elif raw_line.startswith("--- a/") and current_file["display_path"] == "/dev/null":
                    current_file["display_path"] = raw_line[len("--- a/") :].strip()
                    current_file["file_path"] = current_file["display_path"]
                elif raw_line.startswith("rename to "):
                    current_file["display_path"] = raw_line[len("rename to ") :].strip()
                    current_file["file_path"] = current_file["display_path"]
                elif raw_line.startswith("rename from ") and not current_file.get("file_path"):
                    current_file["display_path"] = raw_line[len("rename from ") :].strip()
                    current_file["file_path"] = current_file["display_path"]
                continue

            hunk_match = HUNK_RE.match(raw_line)
            if hunk_match:
                old_line = int(hunk_match.group(1))
                new_line = int(hunk_match.group(3))
                current_hunk = {
                    "header": raw_line,
                    "meta": (hunk_match.group(5) or "").strip(),
                    "lines": [],
                }
                current_file["hunks"].append(current_hunk)
                continue

            if current_hunk is None:
                current_file["headers"].append(raw_line)
                continue

            if raw_line.startswith("+") and not raw_line.startswith("+++"):
                line = {
                    "kind": "add",
                    "text": raw_line,
                    "old_line": 0,
                    "new_line": new_line,
                    "side": "new",
                }
                new_line += 1
            elif raw_line.startswith("-") and not raw_line.startswith("---"):
                line = {
                    "kind": "del",
                    "text": raw_line,
                    "old_line": old_line,
                    "new_line": 0,
                    "side": "old",
                }
                old_line += 1
            else:
                line = {
                    "kind": "ctx",
                    "text": raw_line,
                    "old_line": old_line,
                    "new_line": new_line,
                    "side": "new",
                }
                old_line += 1
                new_line += 1
            current_hunk["lines"].append(line)

        return files

    def _get_git_comments_map(self, base_sha, head_sha):
        self.ensure_one()
        result = defaultdict(list)
        comments = self.message_ids.filtered(
            lambda m: m.git_base_sha == base_sha and m.git_head_sha == head_sha and m.git_file_path
        )
        for message in comments.sorted(key=lambda m: (m.date or fields.Datetime.now(), m.id)):
            key = (
                message.git_file_path,
                message.git_old_line or 0,
                message.git_new_line or 0,
                message.git_side or "new",
            )
            result[key].append(
                {
                    "message_id": message.id,
                    "author": message.author_id.display_name or message.email_from or "Unknown",
                    "date": fields.Datetime.to_string(message.date) if message.date else "",
                    "body": self._message_body_to_text(message.body),
                    "side": message.git_side or "new",
                    "old_line": message.git_old_line or 0,
                    "new_line": message.git_new_line or 0,
                }
            )
        return result

    def _build_git_diff_payload(self, raw_diff, base_sha, head_sha):
        self.ensure_one()
        files = self._parse_unified_diff(raw_diff)
        comments_map = self._get_git_comments_map(base_sha, head_sha)
        total_comments = 0

        for file_data in files:
            file_comments = 0
            additions = 0
            deletions = 0
            for hunk in file_data.get("hunks", []):
                for line in hunk.get("lines", []):
                    if line.get("kind") == "add":
                        additions += 1
                    elif line.get("kind") == "del":
                        deletions += 1
                    key = (
                        file_data.get("file_path"),
                        line.get("old_line") or 0,
                        line.get("new_line") or 0,
                        line.get("side") or "new",
                    )
                    comments = comments_map.get(key, [])
                    line["comments"] = comments
                    line["comment_count"] = len(comments)
                    file_comments += len(comments)
                    total_comments += len(comments)
            file_data["comment_count"] = file_comments
            file_data["additions"] = additions
            file_data["deletions"] = deletions

        payload = {
            "status": "ok",
            "file_count": len(files),
            "comment_count": total_comments,
            "empty_message": _("Diff is empty for the current branch comparison.") if not files else "",
            "files": files,
        }
        return json.dumps(payload)

    def _set_git_error_payload(self, error_text):
        payload = {
            "status": "error",
            "error": error_text or _("Unknown error"),
            "files": [],
        }
        return json.dumps(payload)

    def _refresh_git_diff_for_task(self, compare=None):
        self.ensure_one()
        compare = compare or self._git_get_compare_info()
        payload = self._build_git_diff_payload(
            compare["raw_diff"], compare["base_sha"], compare["head_sha"]
        )
        values = {
            "git_diff_raw": compare["raw_diff"],
            "git_diff_payload": payload,
            "git_refresh_error": False,
            "git_last_refresh": fields.Datetime.now(),
        }
        self.write(values)
        compare["payload"] = payload
        compare["last_refresh"] = self.git_last_refresh
        return compare

    def _post_git_inline_comment(self, compare, body, file_path, old_line, new_line, side, hunk_header):
        self.ensure_one()
        anchor = "[%s] %s old:%s new:%s" % (
            side or "new",
            file_path,
            old_line or 0,
            new_line or 0,
        )
        message = self.message_post(
            body="<p><strong>%s</strong></p><p>%s</p>"
            % (
                html.escape(anchor),
                html.escape(body).replace("\n", "<br/>") if body else "",
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        message.write(
            {
                "git_base_sha": compare["base_sha"],
                "git_head_sha": compare["head_sha"],
                "git_file_path": file_path,
                "git_old_line": old_line or 0,
                "git_new_line": new_line or 0,
                "git_side": side or "new",
                "git_hunk_header": hunk_header or False,
            }
        )
        return message

    def action_git_refresh_diff(self):
        for task in self:
            try:
                task._refresh_git_diff_for_task()
            except Exception as exc:
                task.write(
                    {
                        "git_refresh_error": str(exc),
                        "git_diff_payload": task._set_git_error_payload(str(exc)),
                        "git_last_refresh": fields.Datetime.now(),
                    }
                )
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_git_post_inline_comment(self):
        for task in self:
            if not task.git_comment_body:
                raise UserError(_("Please write a comment first."))
            if not task.git_comment_file_path:
                raise UserError(_("Please select a diff line first."))

            compare = task._git_get_compare_info()
            task._post_git_inline_comment(
                compare=compare,
                body=task.git_comment_body,
                file_path=task.git_comment_file_path,
                old_line=task.git_comment_old_line,
                new_line=task.git_comment_new_line,
                side=task.git_comment_side,
                hunk_header=task.git_comment_hunk_header,
            )
            task.write({"git_comment_body": False})
            task._refresh_git_diff_for_task(compare=compare)
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_git_post_inline_comment_widget(self, anchor):
        self.ensure_one()
        body = (anchor or {}).get("body")
        file_path = (anchor or {}).get("file_path")
        old_line = int((anchor or {}).get("old_line") or 0)
        new_line = int((anchor or {}).get("new_line") or 0)
        side = (anchor or {}).get("side") or "new"
        hunk_header = (anchor or {}).get("hunk_header") or False

        if not body:
            raise UserError(_("Please write a comment first."))
        if not file_path:
            raise UserError(_("Please select a diff line first."))

        compare = self._git_get_compare_info()
        self._post_git_inline_comment(
            compare=compare,
            body=body,
            file_path=file_path,
            old_line=old_line,
            new_line=new_line,
            side=side,
            hunk_header=hunk_header,
        )
        compare = self._refresh_git_diff_for_task(compare=compare)
        return {
            "git_diff_payload": compare["payload"],
            "git_diff_raw": compare["raw_diff"],
            "git_refresh_error": False,
            "git_last_refresh": fields.Datetime.to_string(compare["last_refresh"]) if compare.get("last_refresh") else False,
        }
