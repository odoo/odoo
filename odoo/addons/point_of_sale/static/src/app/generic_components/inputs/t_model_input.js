/** @odoo-module */

import { Component } from "@odoo/owl";

/**
 *   tModel is an array that represents the state variable that this component
 *   should read and write to.
 *   ex: normally you would write
 *   ```<input t-model="state.userValues[nThValue].searchString"/>```
 *   with this component you can write
 *   ```<Input tModel="[state.userValues[nThValue], "searchString"]"/>```
 */
export class TModelInput extends Component {
    static props = { tModel: Array };
    getValue(tModel = this.props.tModel) {
        const [obj, key] = tModel;
        return obj[key];
    }
    setValue(newValue, tModel = this.props.tModel) {
        const [obj, key] = tModel;
        obj[key] = newValue;
    }
}
