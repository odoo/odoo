import { Component } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useState } from "@web/owl2/utils";

export function getSkipDialogKey(isPublishing = true, pageOnly = true) {
    const action = isPublishing ? "publish" : "delete";
    const target = pageOnly ? "page" : "website";
    return `website_no_${action}_${target}_draft_dialog`;
}

export class DraftActionDialog extends Component {
    static components = { CheckBox, Dialog };
    static template = "website_builder.DraftDialog";
    static props = {
        pageOnly: { type: Boolean, optional: true },
        isPublishing: { type: Boolean, optional: true },
        confirm: Function,
        discard: Function,
    };
    static defaultProps = {
        pageOnly: true,
        isPublishing: true,
    };

    setup() {
        this.state = useState({ shouldShowAgain: true });
        this.title = _t("Confirmation");
        const action = this.props.isPublishing ? "publish" : "delete";
        const target = this.props.pageOnly ? "page" : "website";
        let body = `You are about to ${action} this ${target}'s draft.`;
        if (this.props.pageOnly) {
            body += ` If you've made changes to the shared components (header, footer, etc), or to the styles, it will ${action} it too.`;
        }
        this.body = _t(body);
    }

    toggleShouldShowAgain() {
        this.state.shouldShowAgain = !this.shouldShowAgain;
    }

    onConfirmClick() {
        if (!this.shouldShowAgain) {
            const localStorageKey = getSkipDialogKey(this.props.isPublishing, this.props.pageOnly);
            browser.localStorage.setItem(localStorageKey, true);
        }
        this.props.confirm();
    }

    onDiscardClick() {
        this.props.discard();
        this.props.close();
    }
}
