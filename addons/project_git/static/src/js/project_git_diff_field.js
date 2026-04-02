/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useState } from "@odoo/owl";

export class ProjectGitDiffField extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            expandedFiles: {},
            activeComposer: null,
            draft: "",
            submitting: false,
            fileFilter: "",
        });
    }

    get payload() {
        const value = (this.props.record && this.props.name && this.props.record.data) ? this.props.record.data[this.props.name] : this.props.value;
        if (!value) {
            return { status: "empty", files: [], empty_message: "No diff loaded yet." };
        }
        try {
            const parsed = JSON.parse(value);
            if (!parsed || typeof parsed !== "object") {
                return { status: "error", error: "Invalid diff payload.", files: [] };
            }
            if (!Array.isArray(parsed.files)) {
                parsed.files = [];
            }
            return parsed;
        } catch (_error) {
            return {
                status: "error",
                error: "Could not parse diff payload.",
                files: [],
            };
        }
    }

    get visibleFiles() {
        const payload = this.payload;
        const term = (this.state.fileFilter || "").trim().toLowerCase();
        const files = payload.files || [];
        if (!term) {
            return files;
        }
        return files.filter((file) => (file.display_path || file.file_path || "").toLowerCase().includes(term));
    }

    get recordId() {
        return this.props.record && this.props.record.resId;
    }

    onFilterInput(ev) {
        this.state.fileFilter = ev.target.value || "";
    }

    isExpanded(file, index) {
        const key = this.fileKey(file, index);
        if (!(key in this.state.expandedFiles)) {
            return true;
        }
        return !!this.state.expandedFiles[key];
    }

    toggleFileByKey(key) {
        const current = key in this.state.expandedFiles ? !!this.state.expandedFiles[key] : true;
        this.state.expandedFiles[key] = !current;
    }

    onToggleFile(ev) {
        const key = ev.currentTarget.dataset.fileKey || "";
        if (key) {
            this.toggleFileByKey(key);
        }
    }

    fileKey(file, index) {
        return `${file.file_path || file.display_path || "file"}:${index}`;
    }

    hunkKey(file, hunk, index) {
        return `${file.file_path || file.display_path || "file"}:${hunk.header || "hunk"}:${index}`;
    }

    lineKey(file, hunk, line, index) {
        return [
            file.file_path || file.display_path || "file",
            hunk.header || "hunk",
            line.old_line || 0,
            line.new_line || 0,
            line.kind || "ctx",
            index,
        ].join(":");
    }

    commentKey(comment, index) {
        return [
            comment.message_id || 0,
            comment.author || "author",
            comment.date || "date",
            index,
        ].join(":");
    }

    lineClass(file, line) {
        const selected = this.isComposerOpen(file, line) ? " o_pg_selected" : "";
        if (line.kind === "add") {
            return `o_pg_line o_pg_line_add${selected}`;
        }
        if (line.kind === "del") {
            return `o_pg_line o_pg_line_del${selected}`;
        }
        return `o_pg_line o_pg_line_ctx${selected}`;
    }

    displayLineNo(value) {
        return value || "";
    }

    codeText(line) {
        return line.text || "";
    }

    countLabel(count, singular, plural) {
        return `${count} ${count === 1 ? singular : plural}`;
    }

    anchorLabel(line) {
        if (line.side === "old") {
            return `old:${line.old_line || 0}`;
        }
        return `new:${line.new_line || 0}`;
    }

    onOpenComposer(ev) {
        const dataset = ev.currentTarget.dataset || {};
        this.state.activeComposer = {
            file_path: dataset.filePath || "",
            hunk_header: dataset.hunkHeader || "",
            old_line: Number(dataset.oldLine || 0),
            new_line: Number(dataset.newLine || 0),
            side: dataset.side || "new",
        };
        this.state.draft = "";
    }

    closeComposer() {
        this.state.activeComposer = null;
        this.state.draft = "";
    }

    onComposerInput(ev) {
        this.state.draft = ev.target.value || "";
    }

    isComposerOpen(file, line) {
        const active = this.state.activeComposer;
        if (!active) {
            return false;
        }
        return active.file_path === (file.file_path || file.display_path || "")
            && (active.old_line || 0) === (line.old_line || 0)
            && (active.new_line || 0) === (line.new_line || 0)
            && (active.side || "new") === (line.side || "new");
    }

    async submitComposer() {
        const active = this.state.activeComposer;
        if (!active) {
            return;
        }
        if (!this.recordId) {
            this.notification.add("Save the task first before posting inline comments.", { type: "warning" });
            return;
        }
        const body = (this.state.draft || "").trim();
        if (!body) {
            this.notification.add("Write a comment first.", { type: "warning" });
            return;
        }
        this.state.submitting = true;
        try {
            const result = await this.orm.call(
                "project.task",
                "action_git_post_inline_comment_widget",
                [[this.recordId], {
                    ...active,
                    body,
                }]
            );
            if (result) {
                this.props.record.update({
                    git_diff_payload: result.git_diff_payload || this.props.value,
                    git_refresh_error: result.git_refresh_error || false,
                });
            }
            this.closeComposer();
            this.notification.add("Inline comment posted.", { type: "success" });
            await this.action.doAction({ type: "ir.actions.client", tag: "reload" });
        } catch (error) {
            const message = (error && error.message) || "Could not post the inline comment.";
            this.notification.add(message, { type: "danger" });
            console.error(error);
        } finally {
            this.state.submitting = false;
        }
    }
}

ProjectGitDiffField.template = "project_git.ProjectGitDiffField";
ProjectGitDiffField.props = { ...standardFieldProps };
ProjectGitDiffField.supportedTypes = ["text"];

registry.category("fields").add("project_git_diff", {
    component: ProjectGitDiffField,
    supportedTypes: ["text"],
});
