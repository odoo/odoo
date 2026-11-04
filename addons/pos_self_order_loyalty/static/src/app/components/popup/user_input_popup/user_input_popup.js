import { Component, signal, useProps, t } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useAutofocus } from "@web/core/utils/hooks";

export class UserInputPopup extends Component {
    static template = "pos_self_order_loyalty.UserInputPopup";

    inputRef = signal.ref();

    setup() {
        useAutofocus({ ref: this.inputRef, mobile: true });
        this.props = useProps({
            text: t.string(),
            getPayload: t.function(),
            close: t.function(),
            useMobileScanner: t.boolean().optional(false),
            inputPlaceholder: t.string().optional(""),
            isValid: t.function().optional(() => () => true),
        });
        this.selfOrder = useSelfOrder();
        this.input = signal("");
    }

    confirm() {
        this.props.getPayload(this.input());
        this.props.close();
    }
}
