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
                const newVal = formatFloat(taxGroup.tax_group_amount, { digits: currency.digits });
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
        this.props.taxGroup.formatted_tax_group_amount = this.props.taxGroup.formatted_tax_group_amount.replace(oldValue.toString(), newValue.toString());
        this.props.onChangeTaxGroup({
            oldValue,
            newValue: newValue,
            taxGroupId: this.props.taxGroup.tax_group_id,
        });
    }
}

TaxGroupComponent.props = {
    currency: {},
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
        super.setup();
        this.totals = this.props.value;
        this.readonly = this.props.readonly;
        onWillUpdateProps((nextProps) => {
            // We only reformat tax groups if there are changed
            this.totals = nextProps.value;
            this.readonly = nextProps.readonly;
        });
    }

    get currencyId() {
        const recordCurrency = this.props.record.data.currency_id;
        return recordCurrency ? recordCurrency[0] : session.company_currency_id;
    }

    get currency() {
        return session.currencies[this.currencyId];
    }

    invalidate() {
        return this.props.record.setInvalidField(this.props.name);
    }

    /**
     * This method is the main function of the tax group widget.
     * It is called by the TaxGroupComponent and receives the
     * newer tax value.
     *
     * It is responsible for calculating taxes based on tax groups and triggering
     * an event to notify the ORM of a change.
     */
    _onChangeTaxValueByTaxGroup({ oldValue, newValue, taxGroupId }) {
        if (oldValue === newValue) return;
        this._computeTotalsFormat();
        this.totals.amount_total = this.totals.amount_untaxed + newValue;
        this.props.update(this.totals);
    }

    _format(amount) {
        return formatMonetary(amount, { currencyId: this.currencyId });
    }

    _computeTotalsFormat() {
        if (!this.totals) {
            return;
        }
        let amount_untaxed = this.totals.amount_untaxed;
        let amount_tax = 0;
        let subtotals = [];
        for (let subtotal_title of this.totals.subtotals_order) {
            let amount_total = amount_untaxed - amount_tax;
            subtotals.push({
                'name': subtotal_title,
                'amount': amount_total,
                'formatted_amount': this._format(amount_total),
            });
            for (let group_name of Object.keys(this.totals.groups_by_subtotal)) {
                let group = this.totals.groups_by_subtotal[group_name];
                for (let i in group) {
                    amount_tax = amount_tax + group[i].tax_group_amount;
                }
            }
        }
        this.totals.subtotals = subtotals;
        let amount_total = amount_untaxed + amount_tax;
        this.totals.amount_total = amount_total;
        this.totals.formatted_amount_total = this._format(amount_total);
        for (let group_name of Object.keys(this.totals.groups_by_subtotal)) {
            let group = this.totals.groups_by_subtotal[group_name];
            for (let i in group) {
                group[i].formatted_tax_group_amount = this._format(group[i].tax_group_amount);
                group[i].formatted_tax_group_base_amount = this._format(group[i].tax_group_base_amount);
            }
        }
    }
}
TaxTotalsComponent.template = "account.TaxTotalsField";
TaxTotalsComponent.components = { TaxGroupComponent };
TaxTotalsComponent.props = {
    ...standardFieldProps,
};

registry.category("fields").add("account-tax-totals-field", TaxTotalsComponent);
