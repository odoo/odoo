/** @odoo-module */

import { AbstractMacro } from "@knowledge/macros/abstract_macro";
import { pasteElements } from "@knowledge/macros/utils";

/**
 * Macro that will open the Full Composer Form view dialog in the Form view
 * context of a target record, and paste text content inside it. Does not
 * actually send the message.
 */
export class SendAsMessageMacro extends AbstractMacro {
    /**
     * @override
     * @returns {Array[Object]}
     */
    macroAction() {
        const action = super.macroAction();
        let sendMessageLastClickedEl = null;
        action.steps.push({
            // Search for the chatter button to send a message and make sure
            // that the composer is visible. Search in notebook tabs too.
            trigger: function() {
                this.validatePage();
                const el = this.getFirstVisibleElement('.o-mail-Chatter-sendMessage:not([disabled])');
                if (el) {
                    if (el.classList.contains('active')) {
                        return el;
                    } else if (el !== sendMessageLastClickedEl) {
                        el.click();
                        sendMessageLastClickedEl = el;
                    }
                } else {
                    this.searchInXmlDocNotebookTab('.oe_chatter');
                }
                return null;
            }.bind(this),
            action: () => {},
        }, {
            // Open the full composer Form view Dialog.
            trigger: function() {
                this.validatePage();
                return this.getFirstVisibleElement('.o-mail-Composer-fullComposer:not([disabled])');
            }.bind(this),
            action: 'click',
        }, {
            // Paste the html data inside the message body.
            trigger: function () {
                this.validatePage();
                const dialog = this.getFirstVisibleElement('.o_dialog .o_mail_composer_form');
                if (dialog) {
                    return this.getFirstVisibleElement(dialog.querySelector('.o_field_html[name="body"] .odoo-editor-editable'));
                }
                return null;
            }.bind(this),
            action: pasteElements.bind(this, this.data.dataTransfer),
        }, this.unblockUI);
        return action;
    }
}

/**
 * Macro that will append content in the target record's html field in its Form
 * view. Does not trigger the save (field will be dirty).
 */
export class UseAsDescriptionMacro extends AbstractMacro {
    /**
     * @override
     * @returns {Array[Object]}
     */
    macroAction() {
        const action = super.macroAction();
        action.steps.push({
            // Ensure that the Form view is editable
            trigger: function () {
                return this.getFirstVisibleElement('.o_form_editable');
            }.bind(this),
            action: () => {},
        }, {
            // Search for the target html field and ensure that it is editable.
            // Search in notebook tabs too.
            trigger: function () {
                this.validatePage();
                const el = this.getFirstVisibleElement(
                    `.o_field_html[name="${this.data.fieldName}"]`,
                    (element) => element.querySelector('.odoo-editor-editable'),
                );
                if (el) {
                    return el;
                }
                if (this.data.pageName) {
                    this.searchInXmlDocNotebookTab(`page[name="${this.data.pageName}"]`);
                }
                return null;
            }.bind(this),
            action: 'click',
        }, {
            // Search for the editable element. Paste the html data inside the
            // field.
            trigger: function () {
                this.validatePage();
                return this.getFirstVisibleElement(`.o_field_html[name="${this.data.fieldName}"] .odoo-editor-editable`);
            }.bind(this),
            action: function (el) {
                const wysiwyg = $(el).data('wysiwyg');
                wysiwyg._onHistoryResetFromSteps = () => {
                    pasteElements(this.data.dataTransfer, el);
                    wysiwyg._onHistoryResetFromSteps = undefined;
                };
                pasteElements(this.data.dataTransfer, el);
            }.bind(this),
        }, this.unblockUI);
        return action;
    }
}
