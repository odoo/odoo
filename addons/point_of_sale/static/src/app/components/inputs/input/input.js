import { useRef } from "@web/owl2/utils";
import { onPatched, props, proxy, t } from "@odoo/owl";
import { useAutofocus } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import { TModelInput } from "@point_of_sale/app/components/inputs/t_model_input";
/**
 *   This component is meant to provide a "batteries included" api for working
 *   with inputs. It is well suited to work as a search bar or as a monetary input.
 *   Optional props allow handling debouncing, toggling between mobile and desktop views,
 *   autofocus, validation, and more.
 */
export const inputProps = {
    tModel: t.array(),
    isSmall: t.boolean().optional(false),
    debounceMillis: t.number().optional(0),
    icon: t.object({ type: t.string().optional(), value: t.string().optional() }).optional({}),
    getRef: t.function().optional(),
    autofocus: t.boolean().optional(false),
    autofocusMobile: t.boolean().optional(false),
    iconOnLeftSide: t.boolean().optional(true),
    isValid: t.function().optional(() => () => true),
    placeholder: t.string().optional(""),
    class: t.string().optional(""),
    callback: t.function().optional(),
    isOpenCallback: t.function().optional(),
    readonly: t.boolean().optional(false),
    onBlur: t.function().optional(),
    onClick: t.function().optional(),
};

export class Input extends TModelInput {
    static template = "point_of_sale.input";
    props = props(inputProps);
    setup() {
        this.state = proxy({ isOpen: false });
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
