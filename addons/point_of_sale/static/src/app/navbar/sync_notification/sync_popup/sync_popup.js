/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { SaleDetailsButton } from "@point_of_sale/app/navbar/sale_details_button/sale_details_button";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

export class SyncPopup extends Component {
    static components = { SaleDetailsButton, Input, Dialog };
    static template = "point_of_sale.SyncPopup";
    static props = ["close", "confirm"];

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
    }
    getCount(data) {
        return data.values ? 1 : data.args.length;
    }
    delete(uuid) {
        this.dialog.add(ConfirmationDialog, {
            title: _t("Delete pending record?"),
            body: _t(
                "Please note that this operation will result in the loss of any data not saved on the server."
            ),
            confirm: () => {
                this.pos.data.deleteUnsyncData(uuid);
            },
        });
    }
    async confirm() {
        this.props.confirm();
        this.props.close();
    }
}
