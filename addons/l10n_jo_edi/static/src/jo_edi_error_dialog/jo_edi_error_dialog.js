import { browser } from "@web/core/browser/browser";
import { RPCErrorDialog } from "@web/core/errors/error_dialogs";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class JoFotaraErrorDialog extends RPCErrorDialog {
    static template = "l10n_jo_edi.JoFotaraErrorDialog";

    setup() {
        super.setup();
        const { data } = this.props;
        this.message = data.arguments?.[0] || this.props.message;
        this.xmlUrl = data.context.l10n_jo_edi.xml_url;
    }

    inferTitle() {
        this.title = _t("JoFotara");
    }

    onClickClipboard() {
        browser.navigator.clipboard.writeText(this.message);
        this.showTooltip();
    }
}

// keyed on the exception's dotted path: the "exception_class" hook is only consulted for
// exceptions the registry does not already know, and UserError is one it knows.
registry
    .category("error_dialogs")
    .add("odoo.addons.l10n_jo_edi.models.account_move_send.JoFotaraRejection", JoFotaraErrorDialog);
