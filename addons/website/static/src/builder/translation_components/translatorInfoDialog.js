import { Component, useProps, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { WebsiteDialog } from "@website/components/dialog/dialog";

export const localStorageNoDialogKey = "website_translator_nodialog";

export class TranslatorInfoDialog extends Component {
    static components = { WebsiteDialog };
    static template = "website_builder.TranslatorInfoDialog";
    props = useProps({
        close: t.function(),
    });
    setup() {
        this.strongOkButton = _t("Ok, never show me this again");
        this.okButton = _t("Ok");
    }

    onStrongOkClick() {
        localStorage.setItem(localStorageNoDialogKey, true);
    }
}
