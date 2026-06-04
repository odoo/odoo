import { Component, proxy, props, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class NumberPopup extends Component {
    static template = "pos_self_order.NumberPopup";
    static components = { Dialog };

    props = props({
        title: t.string().optional(_t("Enter Amount")),
        startingValue: t.string().optional(""),
        startingType: t.string().optional("fixed"),
        types: t.array(t.object()).optional(() => []),
        getPayload: t.function().optional(),
        close: t.function().optional(),
    });

    setup() {
        this.ui = useService("ui");
        this.state = proxy({
            buffer: String(this.props.startingValue),
            type: this.props.startingType,
            isInitial: true,
        });
    }

    input(value) {
        if (this.state.isInitial) {
            this.state.buffer = "";
            this.state.isInitial = false;
        }
        if (value === "Backspace") {
            this.state.buffer = this.state.buffer.slice(0, -1);
            return;
        }
        if (value === "." && this.state.buffer.includes(".")) {
            return;
        }
        this.state.buffer += value;
    }

    get currentType() {
        return this.props.types.find((type) => type.name === this.state.type);
    }

    get currentSymbol() {
        return this.currentType.symbol || "";
    }

    selectType(name) {
        this.state.type = name;
    }

    confirm() {
        this.props.getPayload({
            value: this.state.buffer,
            type: this.state.type,
        });
        this.props.close();
    }

    cancel() {
        this.props.close();
    }
}
