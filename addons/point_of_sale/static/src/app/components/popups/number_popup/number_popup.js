import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Component, proxy, props, types } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { Numpad, buttonsType } from "@point_of_sale/app/components/numpad/numpad";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";

export class NumberPopup extends Component {
    static template = "point_of_sale.NumberPopup";
    static components = { Numpad, Dialog };
    props = props(
        {
            "title?": types.string(),
            "subtitle?": types.string(),
            "buttons?": buttonsType,
            "startingValue?": types.or([types.number(), types.string()]),
            "types?": types.array(
                types.object({
                    name: types.string(),
                    symbol: types.string(),
                })
            ),
            "startingType?": types.string(),
            "feedback?": types.function(),
            "formatDisplayedValue?": types.function(),
            "placeholder?": types.string(),
            "isValid?": types.function(),
            "confirmButtonLabel?": types.string(),
            getPayload: types.function(),
            close: types.function(),
        },
        {
            title: _t("Amount of guests"),
            startingValue: "",
            isValid: () => true,
            formatDisplayedValue: (x) => x,
            feedback: () => false,
        }
    );

    setup() {
        this.numberBuffer = useService("number_buffer");
        this.numberBuffer.use({
            triggerAtInput: ({ buffer }) => (this.state.buffer = buffer),
        });
        useHotkey("enter", () => this.confirm());
        useHotkey("escape", () => this.cancel());

        const defaultType =
            this.props.types?.find((type) => type.name === this.props.startingType) ||
            this.props.types?.[0];
        this.state = proxy({
            buffer: this.props.startingValue,
            type: defaultType,
        });
    }

    get confirmButtonLabel() {
        return this.props.confirmButtonLabel || _t("Confirm");
    }

    confirm() {
        this.props.getPayload(this.state.buffer, this.state.type?.name);
        this.props.close();
    }

    cancel() {
        this.props.close();
    }
}
