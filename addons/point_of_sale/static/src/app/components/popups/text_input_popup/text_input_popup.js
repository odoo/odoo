import { useRef } from "@web/owl2/utils";
import { Component, onMounted, proxy, props, types } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class TextInputPopup extends Component {
    static template = "point_of_sale.TextInputPopup";
    static components = { Dialog };
    props = props(
        {
            title: types.string(),
            "size?": types.string(),
            "buttons?": types.array(),
            "startingValue?": types.string(),
            "placeholder?": types.string(),
            "rows?": types.number(),
            getPayload: types.function(),
            close: types.function(),
        },
        {
            startingValue: "",
            placeholder: "",
            size: "lg",
            rows: 1,
            buttons: [],
        }
    );

    setup() {
        this.state = proxy({ inputValue: this.props.startingValue });
        this.inputRef = useRef("input");
        onMounted(this.onMounted);
    }
    onMounted() {
        this.inputRef.el.focus();
        this.inputRef.el.select();
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
