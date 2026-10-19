import { Component, useProps, proxy, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";
import { useService } from "@web/core/utils/hooks";
import { BACKSPACE, DECIMAL, Numpad } from "@point_of_sale/app/components/numpad/numpad";

export class NumberPopup extends Component {
    static template = "pos_self_order.NumberPopup";
    static components = { Dialog, Numpad };
    props = useProps({
        title: t.string().optional(_t("Enter Amount")),
        startingValue: t.string().optional(""),
        formatDisplayedValue: t.function().optional(() => (value) => value),
        getPayload: t.function(),
        close: t.function(),
    });

    setup() {
        this.ui = useService("ui");
        this.state = proxy({
            buffer: String(this.props.startingValue || ""),
            isInitial: true,
        });
    }

    get buttons() {
        return [1, 2, 3, 4, 5, 6, 7, 8, 9, DECIMAL, 0, BACKSPACE];
    }

    input(value) {
        if (this.state.isInitial && value !== "Backspace") {
            this.state.buffer = "";
            this.state.isInitial = false;
        }
        if (value === "Backspace") {
            this.state.buffer = this.state.buffer.slice(0, -1);
            this.state.isInitial = false;
            return;
        }

        const valueToAdd = value === localization.decimalPoint ? "." : String(value);
        if (valueToAdd === "." && this.state.buffer.includes(".")) {
            return;
        }
        this.state.buffer += valueToAdd;
    }

    get displayedValue() {
        return this.props.formatDisplayedValue(this.state.buffer);
    }

    confirm() {
        this.props.getPayload({ value: this.state.buffer });
        this.props.close();
    }

    cancel() {
        this.props.close();
    }
}
