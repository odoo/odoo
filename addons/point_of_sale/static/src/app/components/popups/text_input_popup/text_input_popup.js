import { useRef } from "@web/owl2/utils";
import { Component, onMounted, props, proxy, t } from "@odoo/owl";
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
<<<<<<< 846830dfcb4ad03b08f883509d8116d50537bf4d:addons/point_of_sale/static/src/app/components/popups/text_input_popup/text_input_popup.js
            ev.preventDefault();
            if (this.state.inputValue.trim()) {
                this.confirm();
            }
||||||| 6ebe743caf6366bf597a6db3070b00d30c1df8ee:addons/point_of_sale/static/src/app/utils/input_popups/text_input_popup.js
            this.confirm();
=======
            ev.stopPropagation();
            this.confirm();
>>>>>>> 0083af441f5b4a9a2445642fd68a5176ebc87886:addons/point_of_sale/static/src/app/utils/input_popups/text_input_popup.js
        }
    }
}
