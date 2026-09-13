// @ts-check
/** @odoo-module native */

import { Component, status, useState } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/ui/dialog/dialog";

const log = makeLogger("web.components.editor_dialog");

export class EditorDialog extends Component {
    static components = { Dialog };

    /** @type {import("services").ServiceFactories["notification"]} */
    notification;
    /** @type {{ value: any, confirming: boolean }} */
    state;

    setup() {
        this.notification = useService("notification");
        this.state = useState({ value: this.initialValue, confirming: false });
    }

    /** @returns {any} */
    get initialValue() {
        throw new Error("EditorDialog: `initialValue` is the subclass's to define");
    }

    /** @returns {string} */
    get invalidMessage() {
        throw new Error("EditorDialog: `invalidMessage` is the subclass's to define");
    }

    /** @returns {Promise<boolean> | boolean} */
    isValueValid() {
        throw new Error("EditorDialog: `isValueValid` is the subclass's to define");
    }

    /** @param {any} value */
    update(value) {
        this.state.value = value;
    }

    async onConfirm() {
        if (this.state.confirming) {
            return;
        }
        const value = this.state.value;
        this.state.confirming = true;
        try {
            const valid = await this.isValueValid();
            if (status(this) === "destroyed" || value !== this.state.value) {
                log.logic("validation discarded");
                return;
            }
            if (!valid) {
                this.notification.add(this.invalidMessage, { type: "danger" });
                return;
            }
            log.logic("confirmation started");
            await this.props.onConfirm(value);
            if (status(this) !== "destroyed" && value === this.state.value) {
                this.props.close();
            }
        } finally {
            this.state.confirming = false;
        }
    }

    onDiscard() {
        this.props.close();
    }
}
