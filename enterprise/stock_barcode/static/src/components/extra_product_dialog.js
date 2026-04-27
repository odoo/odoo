import { CheckBox } from "@web/core/checkbox/checkbox";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { user } from "@web/core/user";
import { onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class ExtraProductDialog extends ConfirmationDialog {
    static template = "stock_barcode.ExtraProductDialog";
    static components = { ...ConfirmationDialog.components, CheckBox };
    static props = {
        ...ConfirmationDialog.props,
        products: Map,
        onCheckboxChange: Function,
    };
    static defaultProps = {
        ...ConfirmationDialog.defaultProps,
        body: _t("Following scanned products are not reserved for this transfer. Are you sure you want to add them?"),
        title: _t("Add extra product?"),
    };

    setup() {
        super.setup();
        onWillStart(async () => {
            this.displayUOM = await user.hasGroup("uom.group_uom");
        });
    }
}
