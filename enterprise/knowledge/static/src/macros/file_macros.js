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
    getSteps() {
        let attachFilesLastClickedEl = null;
        return [
            {
                // Search for the chatter button to attach a file and open
                // the AttachmentList zone. Search in notebook tabs too.
                trigger: () => {
                    this.validatePage();
                    const el = this.getFirstVisibleElement(
                        ".o-mail-Chatter-attachFiles:not([disabled])",
                        (matchEl) => {
                            // Wait for the attachments to be loaded by the chatter.
                            const attachmentsCountEl = matchEl.querySelector("sup");
                            return (
                                attachmentsCountEl &&
                                Number.parseInt(attachmentsCountEl.textContent) > 0
                            );
                        }
                    );
                    if (el) {
                        const attachmentBoxEl = this.getFirstVisibleElement(
                            ".o-mail-AttachmentBox .o-mail-AttachmentList"
                        );
                        if (attachmentBoxEl) {
                            return attachmentBoxEl;
                        } else if (el !== attachFilesLastClickedEl) {
                            el.click();
                            attachFilesLastClickedEl = el;
                        }
                    } else {
                        this.searchInXmlDocNotebookTab("chatter");
                    }
                    return null;
                },
                action: (el) => el.scrollIntoView(),
            },
            {
                action: () => this.unblockUI(),
            },
        ];
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
    getSteps() {
        let sendMessageLastClickedEl = null;
        return [
            {
                // Search for the chatter button to send a message and make sure
                // that the composer is visible. Search in notebook tabs too.
                trigger: () => {
                    this.validatePage();
                    const el = this.getFirstVisibleElement(
                        ".o-mail-Chatter-sendMessage:not([disabled])"
                    );
                    if (el) {
                        if (el.classList.contains("active")) {
                            return el;
                        } else if (el !== sendMessageLastClickedEl) {
                            el.click();
                            sendMessageLastClickedEl = el;
                        }
                    } else {
                        this.searchInXmlDocNotebookTab("chatter");
                    }
                    return null;
                },
                action: (el) => {
                    el.scrollIntoView();
                },
            },
            {
                // Search for the composer button to attach files and start dragging
                // the data file over it.
                trigger: () => {
                    this.validatePage();
                    return this.getFirstVisibleElement(
                        ".o-mail-Composer-attachFiles:not([disabled])"
                    );
                },
                action: dragAndDrop.bind(this, "dragenter", this.data.dataTransfer),
            },
            {
                // Search for the composer drop zone for attachments and drop the
                // data file into it.
                trigger: () => {
                    this.validatePage();
                    return this.getFirstVisibleElement(".o-mail-Composer-dropzone");
                },
                action: dragAndDrop.bind(this, "drop", this.data.dataTransfer),
            },
            {
                action: () => this.unblockUI(),
            },
        ];
    }
}
