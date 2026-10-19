import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { CopyButton } from "@web/core/copy_button/copy_button";
import { Dialog } from "@web/core/dialog/dialog";
import { EmailSharingInput } from "./email_sharing_input";

import { Component, signal, t, useProps } from "@odoo/owl";

export class SlideShareDialog extends Component {
    static template = "website_slides.SlideShareDialog";
    static components = { Dialog, CopyButton, EmailSharingInput };

    props = useProps({
        category: t.string().optional(),
        close: t.function(),
        documentMaxPage: t.number().optional(),
        emailSharing: t.boolean().optional(),
        embedCode: t.string().optional(),
        id: t.number(),
        isChannel: t.boolean().optional(),
        isFullscreen: t.boolean().optional(),
        name: t.string(),
        url: t.string(),
    });

    codeInputRef = signal.ref();

    setup() {
        this.copyUrlText = _t("Copy Link");
        this.copyEmbedCodeText = _t("Copy Embed Code");
        this.successText = _t("Copied");
    }

    onSocialShareClick(url) {
        browser.open(url, "Share Dialog", "width=626,height=436");
    }

    onPageChange(event) {
        const page = event.currentTarget.value;
        const el = this.codeInputRef();
        if (!el) {
            return;
        }
        const newEmbedCodeValue = el.value.replace(/(page=).*?([^\d]+)/, "$1" + page + "$2");
        el.value = newEmbedCodeValue;
    }
}
