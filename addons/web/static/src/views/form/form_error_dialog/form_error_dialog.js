// @ts-check

/** @module @web/views/form/form_error_dialog/form_error_dialog - Error dialog shown on form save failure with discard/redirect/stay options */

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/ui/dialog/dialog";

/** Error dialog shown when a form save fails while navigating away (discard / redirect / stay). */
export class FormErrorDialog extends Component {
    static template = "web.FormErrorDialog";
    static components = { Dialog };
    static props = {
        message: { type: String, optional: true },
        data: { type: Object },
        onDiscard: Function,
        onStayHere: Function,
        onRedirect: { type: Function, optional: true },
        close: Function,
    };

    setup() {
        this.action = useService("action");
        this.message = this.props.message;
        if (this.props?.data.name === "odoo.exceptions.RedirectWarning") {
            this.message = this.props.data.arguments[0];
            this.redirectAction = this.props.data.arguments[1];
            this.redirectBtnLabel = this.props.data.arguments[2];
            this.additionalContext = this.props.data.arguments[3];
        }
    }

    /** @returns {Promise<void>} execute the redirect action or fall back to doAction */
    async onRedirectBtnClicked() {
        if (this.props.onRedirect) {
            await this.props.onRedirect({
                action: this.redirectAction,
                additionalContext: this.additionalContext,
            });
            this.props.close();
        } else {
            await this.action.doAction(this.redirectAction, {
                additionalContext: this.additionalContext,
                forceLeave: true,
            });
            this.stay();
        }
    }

    /** @returns {Promise<void>} discard changes and close the dialog */
    async discard() {
        await this.props.onDiscard();
        this.props.close();
    }

    /** @returns {Promise<void>} stay on the current form and close the dialog */
    async stay() {
        await this.props.onStayHere();
        this.props.close();
    }
}
