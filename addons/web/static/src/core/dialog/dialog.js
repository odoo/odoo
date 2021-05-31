/** @odoo-module **/

import { useActiveElement } from "../ui_service";

const { Component, hooks, misc, QWeb } = owl;
const { useRef, useSubEnv } = hooks;
const { Portal } = misc;

export class Dialog extends Component {
    setup() {
        this.modalRef = useRef("modal");
        useActiveElement("modal");
        useSubEnv({ inDialog: true });
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
        this.trigger("dialog-closed");
    }
}

Dialog.components = { Portal };
Dialog.props = {
    contentClass: { type: String, optional: true },
    fullscreen: Boolean,
    renderFooter: Boolean,
    renderHeader: Boolean,
    size: {
        type: String,
        validate: (s) => ["modal-xl", "modal-lg", "modal-md", "modal-sm"].includes(s),
    },
    technical: Boolean,
    title: String,
};
Dialog.defaultProps = {
    fullscreen: false,
    renderFooter: true,
    renderHeader: true,
    size: "modal-lg",
    technical: true,
    title: "Odoo",
};
Dialog.template = "web.Dialog";

QWeb.registerComponent("Dialog", Dialog);
