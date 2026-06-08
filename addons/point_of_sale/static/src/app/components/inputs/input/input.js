import { useRef } from "@web/owl2/utils";
import { onPatched, proxy, props, types } from "@odoo/owl";
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
    setup() {
        this.inputProps = props(
            {
                "isSmall?": types.boolean(),
                "debounceMillis?": types.number(),
                "icon?": types.object({ type: types.string(), value: types.string() }),
                "getRef?": types.function(),
                "autofocus?": types.boolean(),
                "autofocusMobile?": types.boolean(),
                "iconOnLeftSide?": types.boolean(),
                "isValid?": types.function(),
                "placeholder?": types.string(),
                "class?": types.string(),
                "callback?": types.function(),
                "isOpenCallback?": types.function(),
                "readonly?": types.boolean(),
                "onBlur?": types.function(),
                "onClick?": types.function(),
            },
            {
                class: "",
                isSmall: false,
                debounceMillis: 0,
                icon: { type: "", value: "" },
                placeholder: "",
                autofocus: false,
                autofocusMobile: false,
                iconOnLeftSide: true,
                isValid: () => true,
                readonly: false,
            }
        );
        this.state = proxy({ isOpen: false });
        // Bind setValue to ensure that 'this' remains the component instance.
        this.setValue = debounce(this.setValue.bind(this), this.inputProps.debounceMillis);
        const ref =
            (this.inputProps.autofocus &&
                useAutofocus({ refName: "input", mobile: this.inputProps.autofocusMobile })) ||
            useRef("input");
        this.inputProps.getRef?.(ref);
        onPatched(() => {
            this.setValue.cancel(true);
        });
    }
    setValue(newValue, tModel = this.props.tModel) {
        super.setValue(newValue, tModel);
        this.props.callback?.(newValue);
    }
}
