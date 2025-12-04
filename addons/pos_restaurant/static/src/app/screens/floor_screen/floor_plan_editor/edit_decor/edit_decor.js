import { Component } from "@odoo/owl";
import { getColors } from "@pos_restaurant/app/services/floor_plan/utils/colors";
import {
    opacityToTransparency,
    transparencyToOpacity,
} from "@pos_restaurant/app/services/floor_plan/utils/utils";
import { useService } from "@web/core/utils/hooks";
import { TextInputPopup } from "@point_of_sale/app/components/popups/text_input_popup/text_input_popup";
import { _t } from "@web/core/l10n/translation";

export class EditDecorProperties extends Component {
    static template = "pos_restaurant.floor_editor.edit_decor_properties";
    static components = {};
    static props = {
        element: { optional: true },
        updateElement: { type: Function },
        moveLayer: { type: Function },
        isTextContentEditable: { optional: true },
    };

    setup() {
        this.dialog = useService("dialog");
    }

    get element() {
        return this.props.element;
    }

    getColors() {
        return getColors();
    }

    selectBorderColor(color) {
        let bgColor = this.element.color;
        if (!color && !bgColor) {
            bgColor = "black";
        }
        this.updateElement({ borderColor: color, color: bgColor });
    }

    updateElement(values, options = {}) {
        this.props.updateElement(this.element.uuid, values, {
            setDefaultValueForGroup: true,
            ...options,
        });
    }

    toggleElementValue(key, value) {
        if (this.element[key] === value) {
            value = null;
        }
        this.updateElement({ [key]: value });
    }

    updateElementValueFromInput(baseProp, event) {
        const { value, prop } = this.formatValue(baseProp, event);
        this.updateElement(
            {
                [prop]: value,
            },
            { batched: true }
        );
    }

    commitElementValueFromInput(baseProp, event) {
        const { value, prop } = this.formatValue(baseProp, event);
        this.updateElement({
            [prop]: value,
        });
    }

    formatValue(prop, event) {
        let value = Number(event.target.value);
        if (this.element.isText && prop === "fontSize") {
            value = value / this.element.scale;
        } else if (prop === "transparency") {
            value = transparencyToOpacity(value);
            prop = "opacity";
        }
        return { prop, value };
    }

    getElementTransparency() {
        return opacityToTransparency(this.element.opacity);
    }

    formatFontSize(value) {
        return Math.round(value);
    }

    addText(prop) {
        const initialValue = this.element[prop] || "";
        const rows = Math.max(2, Math.min(4, initialValue.split(/\r\n|\r|\n/).length));

        this.dialog.add(TextInputPopup, {
            title: _t("Enter your text"),
            rows: rows,
            size: "sm",
            startingValue: initialValue,
            getPayload: async (value) => {
                if (!value.trim().length) {
                    value = null;
                }
                this.updateElement({ [prop]: value });
            },
        });
    }

    editTextOnly() {
        const text = this.element.text;

        this.dialog.add(TextInputPopup, {
            title: _t("Enter your text"),
            rows: 4,
            size: "sm",
            startingValue: text,
            getPayload: async (value) => {
                if (!value.trim().length) {
                    value = null;
                }
                this.updateElement({ text: value });
            },
        });
    }

    moveLayer(position) {
        this.props.moveLayer(this.element.uuid, position);
    }
}
