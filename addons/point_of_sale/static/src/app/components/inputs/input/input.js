import { useRef, useState, onPatched } from "@odoo/owl";
import { useAutofocus } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import { TModelInput } from "@point_of_sale/app/components/inputs/t_model_input";
/**
 *   This component is meant to provide a "batteries included" api for working
 *   with inputs. It is well suited to work as a search bar or as a monetary input.
 *   Optional props allow handling debouncing, toggling between mobile and desktop views,
 *   autofocus, validation, and more.
 */
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
        // Bind setValue to ensure that 'this' remains the component instance.
        this.setValue = debounce(this.setValue.bind(this), this.props.debounceMillis);
        const ref =
            (this.props.autofocus &&
                useAutofocus({ refName: "input", mobile: this.props.autofocusMobile })) ||
            useRef("input");
        this.props.getRef?.(ref);
        onPatched(() => {
            this.setValue.cancel(true);
        });
    }
    setValue(newValue, tModel = this.props.tModel) {
        super.setValue(newValue, tModel);
        this.props.callback?.(newValue);
    }
}
