import { _t } from "@web/core/l10n/translation";

export const NEW_BUTTONS = {
    kanban: ".o_control_panel .o-kanban-button-new",
    list: ".o_control_panel .o_list_button_add",
    form: ".o_control_panel .o_form_button_create",
};

const VERB_TRIGGERS = {
    add_stage: ".o_column_quick_create",
    edit: ".o_kanban_quick_create .o_kanban_edit",
    send: ".o-mail-Chatter-sendMessage",
    log: ".o-mail-Chatter-logNote",
    delete: ".o_cp_action_menus button[data-hotkey='u']",
};

/**
 * @param {Element} [el]
 * @returns {boolean}
 */
function isVisible(el) {
    return Boolean(el?.isConnected && el.getClientRects().length);
}

/**
 * @param {ParentNode} root
 * @param {string} selector
 * @returns {HTMLElement | undefined}
 */
function queryVisible(root, selector) {
    return [...root.querySelectorAll(selector)].find(isVisible);
}

/**
 * An action of a tutorial, as resolved by the server (see
 * `web_tuto.step._resolve_action`): a field, a button or a verb of one of the
 * views of the tutorial. A field is done once focused, a button or a verb once
 * clicked.
 */
export class TutorialAction {
    /**
     * @param {Object} data
     * @param {Object} view the view of the tutorial the action is done in
     * @param {Object} tutorial
     */
    constructor({ content, ...data }, view, tutorial) {
        Object.assign(this, data);
        this.customContent = content;
        this.view = view;
        this.tutorial = tutorial;
    }

    get content() {
        return this.customContent || this.defaultContent;
    }

    get defaultContent() {
        if (this.kind === "field") {
            return _t("Fill in the %s field.", this.label);
        }
        if (this.kind === "button") {
            return this.label ? _t("Click on %s.", this.label) : "";
        }
        return {
            new: _t("Create a new record."),
            add_stage: _t("Add a stage to organize your work."),
            edit: _t("Open the record to see all its details."),
            send: _t("Send a message to the followers."),
            log: _t("Log an internal note."),
            delete: _t("Here you can delete the record."),
        }[this.verb];
    }

    /**
     * @returns {string} the selector of the element(s) doing the action
     */
    get selector() {
        if (this.kind === "field") {
            return `${this.scope} .o_field_widget[name='${this.name}']`;
        }
        if (this.kind === "button") {
            const button = `button[name='${this.name}']`;
            return `${this.scope} ${button}, .modal-footer ${button}`;
        }
        if (this.verb === "new") {
            return this.quick_create
                ? ".o_kanban_group .o_kanban_quick_add"
                : NEW_BUTTONS[this.view_type];
        }
        if (this.verb === "add_stage") {
            return `${VERB_TRIGGERS.add_stage}, ${VERB_TRIGGERS.add_stage} .o_kanban_add`;
        }
        return VERB_TRIGGERS[this.verb];
    }

    /**
     * @param {ParentNode} root
     * @returns {HTMLElement | undefined} the element the pointer points at
     */
    findAnchor(root) {
        const el = queryVisible(root, this.selector);
        if (el && this.kind === "field") {
            return queryVisible(el, "input, textarea, [contenteditable=true]") || el;
        }
        return el;
    }

    /**
     * @param {Element} target the clicked or focused element
     * @param {ParentNode} root
     * @returns {boolean} whether the action is done on that element
     */
    isDoneOn(target, root) {
        const el = target.closest(this.selector);
        return Boolean(el && root.contains(el));
    }
}
