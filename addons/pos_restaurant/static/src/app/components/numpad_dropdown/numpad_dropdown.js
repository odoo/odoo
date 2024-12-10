import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { SIZES, utils } from "@web/core/ui/ui_service";
import {
    getButtons,
    DECIMAL,
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
        this.ui = useState(useService("ui"));
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
        return getButtons([{ ...DECIMAL, disabled: true }, ZERO, BACKSPACE]).map(
            (button, index) => ({
                ...button,
                class: `
                    ${button.class}
                    ${index % 3 === 2 ? "mt-0 ms-0 me-0 mb-1" : "me-1 mb-1 mt-0 ms-0"}
                `,
            })
        );
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
