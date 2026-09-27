import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { MoneyDetailsPopup } from "@point_of_sale/app/components/popups/money_details_popup/money_details_popup";
import { Component, proxy, onMounted, useProps, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { parseFloat } from "@web/views/fields/parsers";
import { Dialog } from "@web/core/dialog/dialog";
import { RPCError } from "@web/core/network/rpc";
import { CashInput } from "@point_of_sale/app/components/inputs/input/cash_input/cash_input";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";

class CustomDialog extends Dialog {
    onEscape() {}
}

export class OpeningControlPopup extends Component {
    static template = "point_of_sale.OpeningControlPopup";
    static components = { Dialog: CustomDialog, CashInput };
    props = useProps({
        close: t.function(),
    });

    setup() {
        this.moneyDetails = null;
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.state = proxy({
            notes: "",
            openingCash: this.pos.formatCurrency(
                this.pos.config._last_opening_balance || 0,
                this.pos.config.currency_id.id,
                { noSymbol: true }
            ),
            ordersByPreset: [],
        });
        this.ui = useService("ui");
        this.getOrderCountByPreset = useTrackedAsync(
            async () =>
                (this.state.ordersByPreset = await this.pos.data.call(
                    "pos.session",
                    "get_order_count_by_preset",
                    [this.pos.session.id]
                ))
        );

        onMounted(() => {
            this.getOrderCountByPreset.call();
        });
    }
    get orderCount() {
        return this.state.ordersByPreset.reduce((total, preset) => total + preset.count, 0);
    }
    async confirm() {
        try {
            await this.pos.data.call(
                "pos.session",
                "set_opening_control",
                [this.pos.session.id, parseFloat(this.state.openingCash), this.state.notes],
                {},
                true
            );
        } catch (error) {
            if (
                error instanceof RPCError &&
                error.data.name === "odoo.exceptions.MissingError" &&
                (await this.pos.isSessionDeleted())
            ) {
                return window.location.reload();
            }
            throw error;
        }
        this.pos.session.state = "opened";
        this.props.close();
    }
    async openDetailsPopup() {
        const action = _t("Cash control - opening");
        await this.pos.openCashbox(action);
        this.dialog.add(MoneyDetailsPopup, {
            moneyDetails: this.moneyDetails,
            action: action,
            getPayload: (payload) => {
                if (payload) {
                    const { total, moneyDetails, moneyDetailsNotes } = payload;
                    this.state.openingCash = this.pos.formatCurrency(
                        total,
                        this.pos.config.currency_id.id,
                        {
                            noSymbol: true,
                        }
                    );
                    if (moneyDetailsNotes) {
                        this.state.notes = moneyDetailsNotes;
                    }
                    this.moneyDetails = moneyDetails;
                }
            },
            context: "Opening",
        });
    }
    handleInputChange() {
        if (!this.pos.isValidFloat(this.state.openingCash)) {
            return;
        }
        this.state.notes = "";
    }
    handleInputBlur() {
        const parsed = parseFloat(this.state.openingCash);
        this.state.openingCash = this.pos.formatCurrency(parsed, this.pos.config.currency_id.id, {
            noSymbol: true,
        });
    }
    get cashMethodCount() {
        return this.pos.config.payment_method_ids.filter((pm) => pm.type === "cash").length;
    }
}
