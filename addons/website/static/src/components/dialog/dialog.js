/** @odoo-module **/

import { Dialog } from '@web/core/dialog/dialog';

export class WebsiteDialog extends Dialog {
    setup() {
        super.setup();
        this.title = this.props.title || this.env._t("Confirmation");
        this.primaryTitle = this.props.primaryTitle || this.env._t("Ok");
        this.secondaryTitle = this.props.secondaryTitle || this.env._t("Cancel");
        this.closeOnClick = this.props.closeOnClick === false ? false : true;
    }

    primaryClick() {
        if (this.props.primaryClick) {
            this.props.primaryClick();
        }
        if (this.closeOnClick) {
            this.close();
        }
    }

    secondaryClick() {
        if (this.props.secondaryClick) {
            this.props.secondaryClick();
        }
        if (this.closeOnClick) {
            this.close();
        }
    }
}
WebsiteDialog.props = {
    ...Dialog.props,
    title: { type: String, optional: true },
    body: { type: String, optional: true },
    primaryTitle: { type: String, optional: true },
    primaryClick: { type: Function, optional: true },
    secondaryTitle: { type: String, optional: true },
    secondaryClick: { type: Function, optional: true },
    closeOnClick: { type: Boolean, optional: true },
    close: { type: Function, optional: true },
};
WebsiteDialog.bodyTemplate = "website.DialogBody";
WebsiteDialog.footerTemplate = "website.DialogFooter";
WebsiteDialog.size = "modal-md";
WebsiteDialog.contentClass = "o_website_dialog";
