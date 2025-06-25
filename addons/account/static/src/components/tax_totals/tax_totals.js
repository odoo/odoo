/** @odoo-module **/

import { formatMonetary } from "@web/views/fields/formatters";
import { formatFloat } from "@web/core/utils/numbers";
import { parseFloat } from "@web/views/fields/parsers";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { registry } from "@web/core/registry";
import {
    Component,
    onPatched,
    onWillUpdateProps,
    onWillRender,
    toRaw,
    useRef,
    useState,
} from "@odoo/owl";
import { useNumpadDecimal } from "@web/views/fields/numpad_decimal_hook";

/**
 A line of some TaxTotalsComponent, giving the values of a tax group.
 **/
class TaxGroupComponent extends Component {
    static props = {
        totals: { optional: true },
        subtotal: { optional: true },
        taxGroup: { optional: true },
        onChangeTaxGroup: { optional: true },
        isReadonly: Boolean,
        invalidate: Function,
    };
    static template = "account.TaxGroupComponent";

    setup() {
        this.inputTax = useRef("taxValueInput");
        this.state = useState({ value: "readonly" });
        onPatched(() => {
            if (this.state.value === "edit") {
                const { taxGroup } = this.props;
                const newVal = formatFloat(taxGroup.tax_amount_currency, { digits: this.props.totals.currency_pd });
                this.inputTax.el.value = newVal;
                this.inputTax.el.focus(); // Focus the input
            }
        });
        onWillUpdateProps(() => {
            this.setState("readonly");
        });
        useNumpadDecimal();
    }

    formatMonetary(value) {
        return formatMonetary(value, {currencyId: this.props.totals.currency_id});
    }

    //--------------------------------------------------------------------------
    // Main methods
    //--------------------------------------------------------------------------

    /**
     * The purpose of this method is to change the state of the component.
     * It can have one of the following three states:
     *  - readonly: display in read-only mode of the field,
     *  - edit: display with a html input field,
     *  - disable: display with a html input field that is disabled.
     *
     * If a value other than one of these 3 states is passed as a parameter,
     * the component is set to readonly by default.
     *
     * @param {String} value
     */
    setState(value) {
        if (["readonly", "edit", "disable"].includes(value)) {
            this.state.value = value;
        }
        else {
            this.state.value = "readonly";
        }
    }

    /**
     * This method handles the "_onChangeTaxValue" event. In this method,
     * we get the new value for the tax group, we format it and we call
     * the method to recalculate the tax lines. At the moment the method
     * is called, we disable the html input field.
     *
     * In case the value has not changed or the tax group is equal to 0,
     * the modification does not take place.
     */
    _onChangeTaxValue() {
        this.setState("disable"); // Disable the input
        const oldValue = this.props.taxGroup.tax_amount_currency;
        let newValue;
        try {
            newValue = parseFloat(this.inputTax.el.value); // Get the new value
        } catch {
            this.inputTax.el.value = oldValue;
            this.setState("edit");
            return;
        }
        // The newValue can"t be equals to 0
        if (newValue === oldValue || newValue === 0) {
            this.setState("readonly");
            return;
        }
        const deltaValue = newValue - oldValue;
        this.props.taxGroup.tax_amount_currency += deltaValue;
        this.props.subtotal.tax_amount_currency += deltaValue;
        this.props.totals.tax_amount_currency += deltaValue;
        this.props.totals.total_amount_currency += deltaValue;

        this.props.onChangeTaxGroup({
            oldValue,
            newValue: newValue,
            taxGroupId: this.props.taxGroup.id,
        });
    }
}

/**
 Widget used to display tax totals by tax groups for invoices, PO and SO,
 and possibly allowing editing them.

 Note that this widget requires the object it is used on to have a
 currency_id field.
 **/
export class TaxTotalsComponent extends Component {
    static template = "account.TaxTotalsField";
    static components = { TaxGroupComponent };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.totals = {};
        this.formatData(this.props);
        onWillRender(() => this.formatData(this.props));
    }

    get readonly() {
        return this.props.readonly;
    }

    invalidate() {
        return this.props.record.setInvalidField(this.props.name);
    }

    formatMonetary(value) {
        return formatMonetary(value, {currencyId: this.totals.currency_id});
    }

    /**
     * This method is the main function of the tax group widget.
     * It is called by the TaxGroupComponent and receives the newer tax value.
     *
     * It is responsible for triggering an event to notify the ORM of a change.
     */
    _onChangeTaxValueByTaxGroup({ oldValue, newValue }) {
        if (oldValue === newValue) return;
        this.props.record.update({ [this.props.name]: this.totals });
        delete this.totals.cash_rounding_base_amount_currency;
    }

    formatData(props) {
        let totals = JSON.parse(JSON.stringify(toRaw(props.record.data[this.props.name])));
        if (!totals) {
            return;
        }
        this.totals = totals;
    }
}

export const taxTotalsComponent = {
    component: TaxTotalsComponent,
};

registry.category("fields").add("account-tax-totals-field", taxTotalsComponent);
