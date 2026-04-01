import { Component } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { WebsiteDialog } from "@website/components/dialog/dialog";

export const localStorageNoDialogKey = "website_translator_nodialog";

export class TranslatorInfoDialog extends Component {
    static components = { WebsiteDialog };
    static template = "website_builder.TranslatorInfoDialog";
    static props = {
        close: Function,
    };
    setup() {
        this.strongOkButton = _t("Ok, never show me this again");
        this.okButton = _t("Ok");
    }

    onStrongOkClick() {
        browser.localStorage.setItem(localStorageNoDialogKey, true);
    }
}
