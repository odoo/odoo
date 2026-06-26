import { Component, onMounted, props, proxy, signal, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class TextInputPopup extends Component {
    static template = "point_of_sale.TextInputPopup";
    static components = { Dialog };
    props = props({
        title: t.string(),
        size: t.string().optional("lg"),
        buttons: t.array().optional([]),
        startingValue: t.string().optional(""),
        placeholder: t.string().optional(""),
        rows: t.number().optional(1),
        getPayload: t.function(),
        close: t.function(),
    });

    setup() {
        this.state = proxy({ inputValue: this.props.startingValue });
        this.inputRef = signal.ref();
        onMounted(this.onMounted);
    }
    onMounted() {
        const inputEl = this.inputRef();
        inputEl.focus();
        inputEl.select();
    }
    confirm() {
        this.props.getPayload(this.state.inputValue);
        this.props.close();
    }

    close() {
        this.props.close();
    }

    buttonClick(button) {
        const lines = this.state.inputValue.split("\n").filter((line) => line !== "");
        if (lines.includes(button.label)) {
            this.state.inputValue = lines.filter((line) => line !== button.label).join("\n");
            button.isSelected = false;
        } else {
            this.state.inputValue = lines.join("\n");
            this.state.inputValue += (lines.length > 0 ? "\n" : "") + button.label;
            button.isSelected = true;
        }
    }

    onKeydown(ev) {
        if (this.props.rows === 1 && ev.key.toUpperCase() === "ENTER") {
            ev.preventDefault();
            if (this.state.inputValue.trim()) {
                this.confirm();
            }
        }
    }
}
