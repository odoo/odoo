/** @odoo-module **/

import { formatFloat, formatMonetary } from "@web/views/fields/formatters";
import { parseFloat } from "@web/views/fields/parsers";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { registry } from "@web/core/registry";
import { session } from "@web/session";

const { Component, onPatched, onWillUpdateProps, useRef, useState } = owl;

/**
 A line of some TaxTotalsComponent, giving the values of a tax group.
 **/
class TaxGroupComponent extends Component {
    setup() {
        this.inputTax = useRef("taxValueInput");
        this.state = useState({ value: "readonly" });
        onPatched(() => {
            if (this.state.value === "edit") {
                const { taxGroup, currency } = this.props;
                const newVal = formatFloat(taxGroup.tax_group_amount, { digits: (currency && currency.digits) });
                this.inputTax.el.value = newVal;
                this.inputTax.el.focus(); // Focus the input
            }
        });
        onWillUpdateProps(() => {
            this.setState("readonly");
        });
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
        const oldValue = this.props.taxGroup.tax_group_amount;
        let newValue;
        try {
            newValue = parseFloat(this.inputTax.el.value); // Get the new value
        } catch (_err) {
            this.inputTax.el.value = oldValue;
            this.setState("edit");
            return;
        }
        // The newValue can"t be equals to 0
        if (newValue === oldValue || newValue === 0) {
            this.setState("readonly");
            return;
        }
        this.props.taxGroup.tax_group_amount = newValue;

        this.props.onChangeTaxGroup({
            oldValue,
            newValue: newValue,
            taxGroupId: this.props.taxGroup.tax_group_id,
        });
    }
}

TaxGroupComponent.props = {
    currency: { optional: true },
    taxGroup: { optional: true },
    onChangeTaxGroup: { optional: true },
    isReadonly: Boolean,
    invalidate: Function,
};
TaxGroupComponent.template = "account.TaxGroupComponent";

/**
 Widget used to display tax totals by tax groups for invoices, PO and SO,
 and possibly allowing editing them.

 Note that this widget requires the object it is used on to have a
 currency_id field.
 **/
export class TaxTotalsComponent extends Component {
    setup() {
        this.totals = {};
        this.formatData(this.props);
        onWillUpdateProps((nextProps) => {
            this.formatData(nextProps);
        });
    }

    get readonly() {
        return this.props.readonly;
    }

    get currencyId() {
        const recordCurrency = this.props.record.data.currency_id;
        return recordCurrency && recordCurrency[0];
    }

    get currency() {
        return session.currencies[this.currencyId];
    }

    invalidate() {
        return this.props.record.setInvalidField(this.props.name);
    }

    /**
     * This method is the main function of the tax group widget.
     * It is called by the TaxGroupComponent and receives the newer tax value.
     *
     * It is responsible for triggering an event to notify the ORM of a change.
     */
    _onChangeTaxValueByTaxGroup({ oldValue, newValue }) {
        if (oldValue === newValue) return;
        this.props.update(this.totals);
        this.totals.display_rounding = false;
    }

    formatData(props) {
        let totals = JSON.parse(JSON.stringify(props.value));
        const currencyFmtOpts = { currencyId: props.record.data.currency_id && props.record.data.currency_id[0] };

        let amount_untaxed = totals.amount_untaxed;
        let amount_tax = 0;
        let subtotals = [];
        for (let subtotal_title of totals.subtotals_order) {
            let amount_total = amount_untaxed + amount_tax;
            subtotals.push({
                'name': subtotal_title,
                'amount': amount_total,
                'formatted_amount': formatMonetary(amount_total, currencyFmtOpts),
            });
            let group = totals.groups_by_subtotal[subtotal_title];
            for (let i in group) {
                amount_tax = amount_tax + group[i].tax_group_amount;
            }
        }
        totals.subtotals = subtotals;
        let rounding_amount = totals.display_rounding && totals.rounding_amount || 0;
        let amount_total = amount_untaxed + amount_tax + rounding_amount;
        totals.amount_total = amount_total;
        totals.formatted_amount_total = formatMonetary(amount_total, currencyFmtOpts);
        for (let group_name of Object.keys(totals.groups_by_subtotal)) {
            let group = totals.groups_by_subtotal[group_name];
            for (let key in group) {
                group[key].formatted_tax_group_amount = formatMonetary(group[key].tax_group_amount, currencyFmtOpts);
                group[key].formatted_tax_group_base_amount = formatMonetary(group[key].tax_group_base_amount, currencyFmtOpts);
            }
        }
        this.totals = totals;
    }
}
TaxTotalsComponent.template = "account.TaxTotalsField";
TaxTotalsComponent.components = { TaxGroupComponent };
TaxTotalsComponent.props = {
    ...standardFieldProps,
};

registry.category("fields").add("account-tax-totals-field", TaxTotalsComponent);
