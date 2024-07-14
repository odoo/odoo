/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
// import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";

export class BackorderDialog extends Component {
    setup() {
        this.title = _t("Incomplete Transfer");
    }

    async _onApply() {
        await this.props.onApply();
        this.props.close();
    }
}

BackorderDialog.components = { Dialog };
BackorderDialog.props = {
    displayUoM: Boolean,
    uncompletedLines: Array,
    onApply: Function,
    close: Function,
};
BackorderDialog.template = "stock_barcode.BackorderDialog";
