/** @odoo-module **/
import { MonetaryField, monetaryField } from "@web/views/fields/monetary/monetary_field";

export class BankRecMonetaryField extends MonetaryField{
    static template = "account_accountant.BankRecMonetaryField";
    static props = {
        ...MonetaryField.props,
        hasForcedNegativeValue: { type: Boolean },
    };

    /** Override **/
    get inputOptions(){
        const options = super.inputOptions;
        const parse = options.parse;
        options.parse = (value) => {
            let parsedValue = parse(value);
            if (this.props.hasForcedNegativeValue) {
                parsedValue = -Math.abs(parsedValue);
            }
            return parsedValue;
        };
        return options;
    }

    /** Override **/
    get value() {
        let value = super.value;
        if(this.props.hasForcedNegativeValue){
            value = Math.abs(value);
        }
        return value;
    }
}

export const bankRecMonetaryField = {
    ...monetaryField,
    component: BankRecMonetaryField,
};
