import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { SIZES, utils } from "@web/core/ui/ui_service";
import {
    getButtons,
    EMPTY,
    ZERO,
    BACKSPACE,
    Numpad,
} from "@point_of_sale/app/components/numpad/numpad";

export class NumpadDropdown extends Component {
    static template = "pos_restaurant.NumpadDropdown";
    static props = {};
    static components = { Numpad };

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
        this.numberBuffer = useService("number_buffer");
        this.numberBuffer.use({
            triggerAtEnter: () => this.pos.searchOrder(this.state.buffer),
            triggerAtInput: ({ buffer }) => this.checkIsValid(buffer),
        });
        this.state = useState({
            buffer: "",
            isValidBuffer: true,
        });
    }

    get numpadButtons() {
        const colorClassMap = {
            [BACKSPACE.value]: "o_colorlist_item_color_transparent_1",
        };

        return getButtons([{ ...EMPTY, disabled: true }, ZERO, BACKSPACE]).map((button, index) => ({
            ...button,
            class: `
                ${button.class}
                ${colorClassMap[button.value] || ""}
            `,
        }));
    }

    searchOrder() {
        if (this.state.isValidBuffer) {
            this.pos.searchOrder(this.state.buffer);
        }
    }

    toggleTableSelector() {
        this.pos.tableSelectorState = !this.pos.tableSelectorState;
    }

    get isSmall() {
        return utils.getSize() <= SIZES.VSM;
    }

    checkIsValid(buffer) {
        this.state.buffer = buffer;
        const res = this.pos.findTable(buffer);
        this.state.isValidBuffer = Boolean(res);
    }
}
