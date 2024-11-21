import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";

export const buttonsType = {
    type: Array,
    element: [
        {
            type: Object,
            shape: {
                value: String,
                key: { type: String, optional: true },
                text: { type: String, optional: true },
                symbol: { type: String, optional: true },
                class: { type: String, optional: true },
                disabled: { type: Boolean, optional: true },
            },
        },
        Number,
        String,
    ],
};

export const DECIMAL = {
    get key() {
        return localization.decimalPoint;
    },
    get value() {
        return localization.decimalPoint;
    },
};

export const BACKSPACE = { value: "Backspace", key: "Backspace", text: "⌫" };
export const ZERO = { value: "0" };
export const DEFAULT_LAST_ROW = [{ value: "-", key: "-", text: "+/-" }, ZERO, DECIMAL];
export const EMPTY = { value: "" };

export function getButtons(lastRow, rightColumn) {
    return [
        { value: "1" },
        { value: "2" },
        { value: "3" },
        ...(rightColumn ? [rightColumn[0]] : []),
        { value: "4" },
        { value: "5" },
        { value: "6" },
        ...(rightColumn ? [rightColumn[1]] : []),
        { value: "7" },
        { value: "8" },
        { value: "9" },
        ...(rightColumn ? [rightColumn[2]] : []),
        ...lastRow,
        ...(rightColumn ? [rightColumn[3]] : []),
    ];
}

export function enhancedButtons() {
    return getButtons(DEFAULT_LAST_ROW, [
        { value: "10", text: "+10", symbol: "+" },
        { value: "20", text: "+20", symbol: "+" },
        { value: "50", text: "+50", symbol: "+" },
        BACKSPACE,
    ]);
}

export class Numpad extends Component {
    static template = "point_of_sale.Numpad";
    static props = {
        class: { type: String, optional: true },
        onClick: { type: Function, optional: true },
        buttons: { type: buttonsType, optional: true },
    };
    static defaultProps = {
        class: "numpad",
    };
    get buttons() {
        return this.props.buttons || getButtons([DECIMAL, ZERO, BACKSPACE]);
    }
    setup() {
        if (!this.props.onClick) {
            this.buffer = useService("buffer_service");
            this.onClick = (button) => this.buffer.handleMethodInput(button);
        } else {
            this.onClick = this.props.onClick;
        }
    }
}
