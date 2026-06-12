import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Component, props, proxy, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { Numpad, buttonsType } from "@point_of_sale/app/components/numpad/numpad";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";

export class NumberPopup extends Component {
    static template = "point_of_sale.NumberPopup";
    static components = { Numpad, Dialog };
    props = props({
        title: t.string().optional(_t("Amount of guests")),
        subtitle: t.string().optional(),
        buttons: buttonsType.optional(),
        startingValue: t.or([t.number(), t.string()]).optional(""),
        types: t
            .array(
                t.object({
                    name: t.string(),
                    symbol: t.string(),
                })
            )
            .optional(),
        startingType: t.string().optional(),
        feedback: t.function().optional(() => () => false),
        formatDisplayedValue: t.function().optional(() => (x) => x),
        placeholder: t.string().optional(),
        isValid: t.function().optional(() => () => true),
        confirmButtonLabel: t.string().optional(),
        getPayload: t.function(),
        close: t.function(),
    });

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
