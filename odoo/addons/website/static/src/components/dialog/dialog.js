/** @odoo-module **/

import { Dialog } from '@web/core/dialog/dialog';
import { _t } from "@web/core/l10n/translation";
import { useState, Component } from "@odoo/owl";

const NO_OP = () => {};

export class WebsiteDialog extends Component {
    setup() {
        this.state = useState({
            disabled: false,
        });
    }
    /**
     * Disables the buttons of the dialog when a click is made.
     * If a handler is provided, await for its call.
     * If the prop closeOnClick is true, close the dialog.
     * Otherwise, restore the button.
     *
     * @param handler {function|void} The handler to protect.
     * @returns {function(): Promise} handler called when a click is made.
     */
    protectedClick(handler) {
        return async () => {
            if (this.state.disabled) {
                return;
            }
            this.state.disabled = true;
            if (handler) {
                await handler();
            }
            if (this.props.closeOnClick) {
                return this.props.close();
            }
            this.state.disabled = false;
        }
    }

    get contentClasses() {
        const websiteDialogClass = 'o_website_dialog';
        if (this.props.contentClass) {
            return `${websiteDialogClass} ${this.props.contentClass}`;
        }
        return websiteDialogClass;
    }
}
WebsiteDialog.components = { Dialog };
WebsiteDialog.props = {
    ...Dialog.props,
    primaryTitle: { type: String, optional: true },
    primaryClick: { type: Function, optional: true },
    secondaryTitle: { type: String, optional: true },
    secondaryClick: { type: Function, optional: true },
    showSecondaryButton: { type: Boolean, optional: true },
    close: { type: Function, optional: true },
    closeOnClick: { type: Boolean, optional: true },
    body: { type: String, optional: true },
    slots: { type: Object, optional: true },
    showFooter: { type: Boolean, optional: true },
};
WebsiteDialog.defaultProps = {
    ...Dialog.defaultProps,
    title: _t("Confirmation"),
    showFooter: true,
    primaryTitle: _t("Ok"),
    secondaryTitle: _t("Cancel"),
    showSecondaryButton: true,
    size: "md",
    closeOnClick: true,
    close: NO_OP,
};
WebsiteDialog.template = "website.WebsiteDialog";
