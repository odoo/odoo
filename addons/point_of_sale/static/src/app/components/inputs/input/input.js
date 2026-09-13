/** @odoo-module native */
import {
    onPatched,
    onWillDestroy,
    onWillUpdateProps,
    useRef,
    useState,
} from "@odoo/owl";
import { TModelInput } from "@point_of_sale/app/components/inputs/t_model_input";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useAutofocus } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";

const log = makeLogger("pos.input");
export class Input extends TModelInput {
    static template = "point_of_sale.input";
    static props = {
        ...super.props,
        isSmall: { type: Boolean, optional: true },
        debounceMillis: { type: Number, optional: true },
        icon: {
            type: Object,
            optional: true,
            shape: { type: String, value: String },
        },
        getRef: { type: Function, optional: true },
        autofocus: { type: Boolean, optional: true },
        autofocusMobile: { type: Boolean, optional: true },
        iconOnLeftSide: { type: Boolean, optional: true },
        isValid: { type: Function, optional: true },
        placeholder: { type: String, optional: true },
        class: { type: String, optional: true },
        callback: { type: Function, optional: true },
        isOpenCallback: { type: Function, optional: true },
        readonly: { type: Boolean, optional: true },
    };
    static defaultProps = {
        class: "",
        isSmall: false,
        debounceMillis: 0,
        icon: {},
        placeholder: "",
        autofocus: false,
        autofocusMobile: false,
        iconOnLeftSide: true,
        isValid: () => true,
        readonly: false,
    };
    setup() {
        this.state = useState({ isOpen: false });
        this.setValue = debounce(this.setValue.bind(this), this.props.debounceMillis);
        const ref =
            (this.props.autofocus &&
                useAutofocus({
                    refName: "input",
                    mobile: this.props.autofocusMobile,
                })) ||
            useRef("input");
        this.props.getRef?.(ref);
        onWillUpdateProps(() => {
            // Flush before the binding and callback are replaced by the new props.
            log.logic("flush pending input before updating props");
            this.setValue.cancel(true);
        });
        onPatched(() => {
            this.setValue.cancel(true);
        });
        onWillDestroy(() => {
            log.lifecycle("cancel pending input on destroy");
            this.setValue.cancel();
        });
    }
    setValue(newValue, tModel = this.props.tModel) {
        super.setValue(newValue, tModel);
        this.props.callback?.(newValue);
    }
}
