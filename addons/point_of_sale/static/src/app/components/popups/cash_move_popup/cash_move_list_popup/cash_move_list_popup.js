import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class CashMoveListPopup extends Component {
    static template = "point_of_sale.CashMoveListPopup";
    static components = { Dialog };
    static props = {
        close: { type: Function },
        cashMoves: { type: Array },
        partnerId: { type: Number },
    };
    async setup() {
        super.setup();
        this.pos = usePos();
        this.ui = useService("ui");
        this.callbacks = this.props.cashMoves.reduce(
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
        await this.pos.data.call(
            "pos.session",
            "delete_cash_in_out",
            [[this.pos.session.id], cm.id, this.props.partnerId],
            {},
            true
        );
        this.props.cashMoves = this.props.cashMoves.filter((cashMove) => cashMove.id !== cm.id);
    }
}
