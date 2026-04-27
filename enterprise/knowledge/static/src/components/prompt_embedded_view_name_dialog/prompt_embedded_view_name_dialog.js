/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import {
    Component,
    onMounted,
    useRef } from "@odoo/owl";

export class PromptEmbeddedViewNameDialog extends Component {
    static template = "knowledge.PromptEmbeddedViewNameDialog";
    static components = { Dialog };
    static props = {
        defaultName: { type: String, optional: true },
        isNew: { type: Boolean, optional: true },
        viewType: { type: String },
        save: { type: Function },
        close: { type: Function, optional: true }
    };

    /**
     * @override
     */
    setup () {
        super.setup();
        this.input = useRef('input');
        onMounted(() => {
            window.setTimeout(() => {
                this.input.el?.focus(); // auto-focus
            }, 0);
        });
    }
    async save () {
        await this.props.save(this.input.el.value);
        this.props.close();
    }
    /**
     * @returns {String}
     */
    get placeholder () {
        if (this.props.viewType === 'kanban') {
            return _t('e.g. Buildings');
        }
        if (this.props.viewType === 'list') {
            return _t('e.g. Todos');
        }
    }
    /**
     * @returns {String}
     */
    get title () {
        if (this.props.viewType === 'list') {
            return _t('Insert a List View');
        }
        if (this.props.viewType === 'kanban') {
            return _t('Insert a Kanban View');
        }
        return _t('Embed a View');
    }
    /**
     * @param {Event} event
     */
    onInputKeydown (event) {
        if (event.key === 'Enter') {
            this.save();
        }
    }
}
