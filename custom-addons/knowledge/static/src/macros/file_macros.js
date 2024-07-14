/** @odoo-module */

import { AbstractMacro } from "@knowledge/macros/abstract_macro";
import { dragAndDrop } from "@knowledge/macros/utils";

/**
 * Macro that will add a file as an attachment of a record and display it
 * in its Form view.
 */
export class UseAsAttachmentMacro extends AbstractMacro {
    /**
     * @override
     * @returns {Array[Object]}
     */
    macroAction() {
        const action = super.macroAction();
        let attachFilesLastClickedEl = null;
        action.steps.push({
            // Search for the chatter button to attach a file and open
            // the AttachmentList zone. Search in notebook tabs too.
            trigger: function() {
                this.validatePage();
                const el = this.getFirstVisibleElement('.o-mail-Chatter-attachFiles:not([disabled])', (matchEl) => {
                    // Wait for the attachments to be loaded by the chatter.
                    const attachmentsCountEl = matchEl.querySelector('sup');
                    return attachmentsCountEl && Number.parseInt(attachmentsCountEl.textContent) > 0;
                });
                if (el) {
                    const attachmentBoxEl = this.getFirstVisibleElement('.o-mail-AttachmentBox .o-mail-AttachmentList');
                    if (attachmentBoxEl) {
                        return attachmentBoxEl;
                    } else if (el !== attachFilesLastClickedEl) {
                        el.click();
                        attachFilesLastClickedEl = el;
                    }
                } else {
                    this.searchInXmlDocNotebookTab('.oe_chatter');
                }
                return null;
            }.bind(this),
            action: (el) => el.scrollIntoView(),
        }, this.unblockUI);
        return action;
    }
}

/**
 * Macro that will add a file to a message (without sending it) in the context
 * of a record in its Form view.
 */
export class AttachToMessageMacro extends AbstractMacro {
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
            action: (el) => {
                el.scrollIntoView();
            },
        }, {
            // Search for the composer button to attach files and start dragging
            // the data file over it.
            trigger: function() {
                this.validatePage();
                return this.getFirstVisibleElement('.o-mail-Composer-attachFiles:not([disabled])');
            }.bind(this),
            action: dragAndDrop.bind(this, 'dragenter', this.data.dataTransfer),
        }, {
            // Search for the composer drop zone for attachments and drop the
            // data file into it.
            trigger: function () {
                this.validatePage();
                return this.getFirstVisibleElement('.o-mail-Composer-dropzone');
            }.bind(this),
            action: dragAndDrop.bind(this, 'drop', this.data.dataTransfer),
        }, this.unblockUI);
        return action;
    }
}
