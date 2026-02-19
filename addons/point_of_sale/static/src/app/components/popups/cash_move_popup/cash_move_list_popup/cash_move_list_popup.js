import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class CashMoveListPopup extends Component {
    static template = "point_of_sale.CashMoveListPopup";
    static components = { Dialog };
    static props = {
        close: { type: Function },
    };
    async setup() {
        super.setup();
        this.pos = usePos();
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.callbacks = this.pos.cashMoves.reduce(
            (acc, cm) => ({
                ...acc,
                [cm.id]: useTrackedAsync(() => this.onDeleteCm(cm)),
            }),
            {}
        );
    }

    getStatus(cm) {
        return cm.amount < 0 ? _t("Out") : _t("In");
    }

    getAmount(cm) {
        return this.env.utils.formatCurrency(Math.abs(cm.amount));
    }

    async onDeleteCm(cm) {
        try {
            await this.pos.deleteCashMove(cm.id);
        } catch (error) {
            this.dialog.add(AlertDialog, {
                title: _t("Odoo Server Error"),
                body: error.data.message,
            });
            throw error;
        }
    }

    get hasCashDeletePerm() {
        return this.pos.config._has_cash_delete_perm;
    }
}
