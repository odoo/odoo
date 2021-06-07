/** @odoo-module **/

import { useHotkey } from "../hotkey_hook";
import { useService } from "../service_hook";
import { useActiveElement } from "../ui/ui_service";

const { Component, hooks, misc } = owl;
const { useRef, useSubEnv } = hooks;
const { Portal } = misc;

export class Dialog extends Component {
    constructor(...args) {
        super(...args);
        if (this.constructor === Dialog) {
            throw new Error(
                "Dialog should not be used by itself. Please use the dialog service with a Dialog subclass."
            );
        }
    }
    setup() {
        this.modalRef = useRef("modal");
        this.dialogService = useService("dialog");
        useActiveElement("modal");
        useHotkey(
            "escape",
            () => {
                if (!this.modalRef.el.classList.contains("o_inactive_modal")) {
                    this.close();
                }
            },
            { altIsOptional: true }
        );
        useSubEnv({ inDialog: true });
        this.close = this.close.bind(this);
        this.contentClass = this.constructor.contentClass;
        this.fullscreen = this.constructor.fullscreen;
        this.renderFooter = this.constructor.renderFooter;
        this.renderHeader = this.constructor.renderHeader;
        this.size = this.constructor.size;
        this.technical = this.constructor.technical;
        this.title = this.constructor.title;
        this.__id = null;
    }

    mounted() {
        const dialogContainer = document.querySelector(".o_dialog_container");
        const modals = dialogContainer.querySelectorAll(".o_dialog .modal");
        const len = modals.length;
        for (let i = 0; i < len - 1; i++) {
            const modal = modals[i];
            modal.classList.add("o_inactive_modal");
        }
        dialogContainer.classList.add("modal-open");
    }

    willUnmount() {
        const dialogContainer = document.querySelector(".o_dialog_container");
        const modals = dialogContainer.querySelectorAll(".o_dialog .modal");
        const len = modals.length;
        if (len >= 2) {
            const modal = this.modalRef.el === modals[len - 1] ? modals[len - 2] : modals[len - 1];
            modal.focus();
            modal.classList.remove("o_inactive_modal");
        } else {
            dialogContainer.classList.remove("modal-open");
        }
    }

    /**
     * Send an event signaling that the dialog should be closed.
     * @private
     */
    close() {
        this.dialogService.close(this.__id);
    }
}

Dialog.components = { Portal };
Dialog.template = "web.Dialog";
Dialog.contentClass = null;
Dialog.fullscreen = false;
Dialog.renderFooter = true;
Dialog.renderHeader = true;
Dialog.size = "modal-lg";
Dialog.technical = true;
Dialog.title = "Odoo";
Dialog.bodyTemplate = owl.tags.xml`<div/>`;
Dialog.footerTemplate = "web.DialogFooterDefault";
