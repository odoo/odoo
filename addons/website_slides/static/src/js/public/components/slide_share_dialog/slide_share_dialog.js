import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { CopyButton } from "@web/core/copy_button/copy_button";
import { Dialog } from "@web/core/dialog/dialog";
import { EmailSharingInput } from "./email_sharing_input";

import { Component, useRef } from "@odoo/owl";

export class SlideShareDialog extends Component {
    static template = "website_slides.SlideShareDialog";
    static components = { Dialog, CopyButton, EmailSharingInput };
    static props = {
        category: { type: String, optional: true },
        close: { type: Function },
        documentMaxPage: { type: Number, optional: true },
        emailSharing: { type: Boolean, optional: true },
        embedCode: { type: String, optional: true },
        id: { type: Number },
        isChannel: { type: Boolean, optional: true },
        isFullscreen: { type: Boolean, optional: true },
        name: { type: String },
        url: { type: String },
    };

    setup() {
        this.codeInput = useRef("codeInput");
        this.copyUrlText = _t("Copy Link");
        this.copyEmbedCodeText = _t("Copy Embed Code");
        this.successText = _t("Copied");
    }

    onSocialShareClick(url) {
        browser.open(url, "Share Dialog", "width=626,height=436");
    }

    onPageChange(event) {
        const page = event.currentTarget.value;
        const newEmbedCodeValue = this.codeInput.el.value.replace(/(page=).*?([^\d]+)/, "$1" + page + "$2");
        this.codeInput.el.value = newEmbedCodeValue;
    }
}
