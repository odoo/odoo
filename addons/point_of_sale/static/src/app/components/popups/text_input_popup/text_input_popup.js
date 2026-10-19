import { Component, onMounted, useProps, proxy, signal, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class TextInputPopup extends Component {
    static template = "point_of_sale.TextInputPopup";
    static components = { Dialog };
    props = useProps({
        title: t.string(),
        size: t.string().optional("lg"),
        buttons: t.array().optional([]),
        startingValue: t.string().optional(""),
        placeholder: t.string().optional(""),
        rows: t.number().optional(1),
        removeNewLines: t.boolean().optional(),
        getPayload: t.function(),
        close: t.function(),
    });

    inputRef = signal.ref();
    setup() {
        this.state = proxy({ inputValue: this.props.startingValue });
        onMounted(this.onMounted);
    }
    onMounted() {
        this.inputRef()?.focus();
        this.inputRef()?.select();
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

    onPaste(ev) {
        if (this.props.removeNewLines) {
            ev.preventDefault();
            const pastedText = ev.clipboardData.getData("text");
            const cleanedText = pastedText.replace(/\r?\n/g, "");
            document.execCommand("insertText", false, cleanedText);
        }
    }
}
