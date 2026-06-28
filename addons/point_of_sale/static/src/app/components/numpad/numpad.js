import { useService } from "@web/core/utils/hooks";
import { Component, props, t } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";

export const buttonsType = t.array(
    t.or([
        t.object({
            value: t.string(),
            text: t.string().optional(),
            class: t.string().optional(),
            disabled: t.boolean().optional(),
        }),
        t.number(),
        t.string(),
    ])
);

export const DECIMAL = {
    get value() {
        return localization.decimalPoint;
    },
    class: "o_colorlist_item_numpad_color_6",
};
export const BACKSPACE = {
    value: "Backspace",
    text: "⌫",
    class: "o_colorlist_item_numpad_color_1",
};
export const ZERO = { value: "0" };
export const SWITCHSIGN = { value: "-", text: "+/-" };
export const DEFAULT_LAST_ROW = [SWITCHSIGN, ZERO, DECIMAL];
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
        { value: "+10" },
        { value: "+20" },
        { value: "+50" },
        BACKSPACE,
    ]);
}

export class Numpad extends Component {
    static template = "point_of_sale.Numpad";
    props = props({
        class: t.string().optional("numpad"),
        onClick: t.function().optional(),
        buttons: buttonsType.optional(),
    });
    get buttons() {
        return this.props.buttons || getButtons([DECIMAL, ZERO, BACKSPACE]);
    }
    setup() {
        if (!this.props.onClick) {
            this.numberBuffer = useService("number_buffer");
            this.onClick = (buttonValue) => this.numberBuffer.sendKey(buttonValue);
        } else {
            this.onClick = this.props.onClick;
        }
    }
}
