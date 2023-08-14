/** @odoo-module */

import { Component, useRef, useState } from "@odoo/owl";
import { useAutofocus } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";

/**
 *   This component is meant to provide a "batteries included" api for working
 *   with inputs. It is well suited to work as a search bar or as a monetary input.
 *   Optional props allow handling debouncing, toggling between mobile and desktop views,
 *   autofocus, validation, and more.
 *   The only required prop is tModel, which is an array that represents the
 *   state variable that this component should read and write to. The first
 *   element of the array is the object returned by `useState` and second is
 *   either a `string` or an `int` representing the key to access the value.
 *   ex: normally you would write
 *   ```<input t-model="state.userValues[nThValue].searchString"/>```
 *   with this component you can write
 *   ```<Input tModel="[state.userValues[nThValue], "searchString"]"/>```
 */
export class Input extends Component {
    static template = "point_of_sale.input";
    static props = {
        tModel: Array,
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
    };
    setup() {
        this.state = useState({ isOpen: false });
        this.setValue = debounce(this.setValue, this.props.debounceMillis);
        this.props.getRef?.(
            (this.props.autofocus &&
                useAutofocus({ refName: "input", mobile: this.props.autofocusMobile })) ||
                useRef("input")
        );
    }
    getValue(tModel = this.props.tModel) {
        const [obj, key] = tModel;
        return obj[key];
    }
    setValue(newValue, tModel = this.props.tModel) {
        const [obj, key] = tModel;
        obj[key] = newValue;
        this.props.callback?.(newValue);
    }
}
