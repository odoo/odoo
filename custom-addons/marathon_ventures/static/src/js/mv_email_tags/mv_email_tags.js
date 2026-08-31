/** @odoo-module **/
/*  mv_email_tags - Char field widget that renders a comma-separated
 *  email list as removable chips.
 *
 *  Storage: unchanged. The underlying Char still holds
 *  "a@x.com, b@y.com". We split on commas / semicolons / whitespace
 *  when reading and join with ", " when writing.
 *
 *  Behavior:
 *    * Every email becomes an individual chip with an X.
 *    * Type an email and press Enter (or comma / semicolon / blur)
 *      to add it as a new chip.
 *    * Empty input on Backspace removes the last chip.
 *    * Email format is validated before adding; invalid inputs
 *      shake and show an inline hint.
 *    * Duplicates are silently ignored (case-insensitive).
 */
import { Component, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

// Loose but pragmatic email check: requires local@domain.tld shape.
const EMAIL_RE = /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$/;

function _parseValue(raw) {
    if (!raw) return [];
    return String(raw)
        .split(/[,;\s]+/)
        .map((s) => s.trim())
        .filter(Boolean);
}

function _joinValue(list) {
    return (list || []).join(", ");
}


export class MvEmailTagsField extends Component {
    static template = "marathon_ventures.MvEmailTags";
    static props = { ...standardFieldProps };

    setup() {
        this.inputRef = useRef("input");
        this.state = useState({
            draft: "",
            error: "",
        });
    }

    get emails() {
        return _parseValue(this.props.record.data[this.props.name]);
    }

    get readonly() {
        return this.props.readonly;
    }

    async _commit(list) {
        // Dedup case-insensitively while preserving order.
        const seen = new Set();
        const clean = [];
        for (const e of list) {
            const k = e.toLowerCase();
            if (seen.has(k)) continue;
            seen.add(k);
            clean.push(e);
        }
        await this.props.record.update({
            [this.props.name]: _joinValue(clean),
        });
    }

    async _addOne(value) {
        const email = (value || "").trim().replace(/[,;]+$/, "");
        if (!email) return;
        if (!EMAIL_RE.test(email)) {
            this.state.error = `Not a valid email: ${email}`;
            return;
        }
        this.state.error = "";
        const list = this.emails.slice();
        // Case-insensitive dedup.
        if (list.some((e) => e.toLowerCase() === email.toLowerCase())) {
            this.state.draft = "";
            return;
        }
        list.push(email);
        await this._commit(list);
        this.state.draft = "";
    }

    async onKeydown(ev) {
        // Enter / Tab / , / ; = commit current draft as a new chip.
        if (
            ev.key === "Enter" ||
            ev.key === "Tab" ||
            ev.key === "," ||
            ev.key === ";"
        ) {
            if (this.state.draft.trim()) {
                ev.preventDefault();
                await this._addOne(this.state.draft);
            }
            return;
        }
        // Backspace on an empty input removes the last chip.
        if (
            ev.key === "Backspace" &&
            !this.state.draft &&
            this.emails.length > 0
        ) {
            ev.preventDefault();
            const list = this.emails.slice(0, -1);
            await this._commit(list);
        }
    }

    onInput(ev) {
        this.state.draft = ev.target.value || "";
        if (this.state.error) this.state.error = "";
    }

    async onBlur() {
        if (this.state.draft.trim()) {
            await this._addOne(this.state.draft);
        }
    }

    async onRemove(idx) {
        const list = this.emails.slice();
        list.splice(idx, 1);
        await this._commit(list);
    }

    onWrapperClick(ev) {
        // Clicking anywhere in the wrapper focuses the input, so the
        // whole widget feels tag-like.
        if (this.inputRef.el && ev.target === ev.currentTarget) {
            this.inputRef.el.focus();
        }
    }
}


registry.category("fields").add("mv_email_tags", {
    component: MvEmailTagsField,
    supportedTypes: ["char"],
});
