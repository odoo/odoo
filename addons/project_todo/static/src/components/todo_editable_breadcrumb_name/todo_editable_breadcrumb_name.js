/** @odoo-module */

import { useState, onRendered, useRef } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { CharField } from "@web/views/fields/char/char_field";
import { useAutoresize } from "@web/core/utils/autoresize";

export class TodoEditableBreadcrumbName extends CharField {
    setup() {
        super.setup();
        this.placeholder = _t("Untitled to-do");;
        this.input = useRef("input");

        this.stateTodo = useState({
            isUntitled: true,
        });

        onRendered(() => {
            this.stateTodo.isUntitled = this._isUntitled(this.props.record.data[this.props.name]);
        });
        useAutoresize(this.input);
    }

    /**
     * Check if the name is empty or is the generic name
     * for untitled todos.
     * @param {string} name
     * @returns {boolean}
     */
    _isUntitled(name) {
        name = name && name.trim();
        return !name || name === this.placeholder.toString();
    }

    /**
     * @private
     * @param {InputEvent} ev
     */
    _onFocus(ev) {
        if (this._isUntitled(ev.target.value)) {
            ev.target.value = this.placeholder;
            ev.target.select();
        }
    }

    /**
     * @private
     * @param {InputEvent} ev
     */
    _onInput(ev) {
        const value = ev.target.value;
        this.stateTodo.isUntitled = this._isUntitled(value);
    }
}

TodoEditableBreadcrumbName.template = 'project_todo.TodoEditableBreadcrumbName';
