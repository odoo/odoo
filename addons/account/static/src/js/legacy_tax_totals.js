/** @odoo-module alias=account.tax_group_owl **/
"use strict";

import session from 'web.session';
import AbstractFieldOwl from 'web.AbstractFieldOwl';
import fieldUtils from 'web.field_utils';
import field_registry from 'web.field_registry_owl';
import { LegacyComponent } from "@web/legacy/legacy_component";

const { onPatched, onWillUpdateProps, useRef, useState } = owl;

/**
    A line of some LegacyTaxTotalsComponent, giving the values of a tax group.
**/
class LegacyTaxGroupComponent extends LegacyComponent {
    setup() {
        this.inputTax = useRef('taxValueInput');
        this.state = useState({value: 'readonly'});
        onPatched(this.onPatched);
        onWillUpdateProps(this.onWillUpdateProps);
    }

    //--------------------------------------------------------------------------
    // Life cycle methods
    //--------------------------------------------------------------------------

    onWillUpdateProps(nextProps) {
        this.setState('readonly'); // If props are edited, we set the state to readonly
    }

    onPatched() {
        if (this.state.value === 'edit') {
            let newValue = this.props.taxGroup.tax_group_amount;
            let currency = session.get_currency(this.props.record.data.currency_id.data.id);

            newValue = fieldUtils.format.float(newValue, null, {digits: currency.digits});
            this.inputTax.el.focus(); // Focus the input
            this.inputTax.el.value = newValue;
        }
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
        if (['readonly', 'edit', 'disable'].includes(value)) {
            this.state.value = value;
        }
        else {
            this.state.value = 'readonly';
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
        this.setState('disable'); // Disable the input
        let newValue = this.inputTax.el.value; // Get the new value
        let currency = session.get_currency(this.props.record.data.currency_id.data.id); // The records using this widget must have a currency_id field.
        try {
            newValue = fieldUtils.parse.float(newValue); // Need a float for format the value
            newValue = fieldUtils.format.float(newValue, null, {digits: currency.digits}); // Return a string rounded to currency precision
            newValue = fieldUtils.parse.float(newValue); // Convert back to Float to compare with oldValue to know if value has changed
        } catch (_err) {
            $(this.inputTax.el).addClass('o_field_invalid');
            this.setState('edit');
            return;
        }
        // The newValue can't be equals to 0
        if (newValue === this.props.taxGroup.tax_group_amount || newValue === 0) {
            this.setState('readonly');
            return;
        }
        this.props.taxGroup.tax_group_amount = newValue;
        this.props.onChangeTaxGroup({
            oldValue: this.props.taxGroup.tax_group_amount,
            newValue: newValue,
            taxGroupId: this.props.taxGroup.tax_group_id
        });
    }
}
LegacyTaxGroupComponent.props = ['taxGroup', 'readonly', 'record', 'onChangeTaxGroup'];
LegacyTaxGroupComponent.template = 'account.LegacyTaxGroupComponent';

/**
    Widget used to display tax totals by tax groups for invoices, PO and SO,
    and possibly allowing editing them.

    Note that this widget requires the object it is used on to have a
    currency_id field.
**/
class LegacyTaxTotalsComponent extends AbstractFieldOwl {
    setup() {
        super.setup();
        this.totals = useState({value: this.value ? this.value : null});
        this._computeTotalsFormat()
        this.readonly = this.mode == 'readonly' || this.record.evalModifiers(this.attrs.modifiers).readonly;
        onWillUpdateProps(this.onWillUpdateProps);
    }

    onWillUpdateProps(nextProps) {
        // We only reformat tax groups if there are changed
        this.totals.value = nextProps.record.data[this.props.fieldName];
        this._computeTotalsFormat()
    }

    _onKeydown(ev) {
        switch (ev.which) {
            // Trigger only if the user clicks on ENTER or on TAB.
            case $.ui.keyCode.ENTER:
            case $.ui.keyCode.TAB:
                // trigger blur to prevent the code being executed twice
                $(ev.target).blur();
        }
    }

    /**
     * This method is the main function of the tax group widget.
     * It is called by an event trigger (from the LegacyTaxGroupComponent) and receives
     * a particular payload.
     *
     * It is responsible for calculating taxes based on tax groups and triggering
     * an event to notify the ORM of a change.
     */
    _onChangeTaxValueByTaxGroup(ev) {
        this._computeTotalsFormat();
        this.trigger('field-changed', {
            dataPointID: this.record.id,
            changes: { tax_totals: this.totals.value }
        })
    }

    _format(amount) {
        if (this.props.record.data.currency_id.data) {
            const currency = session.get_currency(this.props.record.data.currency_id.data.id);
            return fieldUtils.format.monetary(amount, null, {currency: currency});
        }
        return fieldUtils.format.monetary(amount);
    }

    _computeTotalsFormat() {
        if (!this.totals.value) // Misc journal entry
            return;
        let amount_untaxed = this.totals.value.amount_untaxed;
        let amount_tax = 0;
        let subtotals = [];
        for (let subtotal_title of this.totals.value.subtotals_order) {
            let amount_total = amount_untaxed + amount_tax;
            subtotals.push({
                'name': subtotal_title,
                'amount': amount_total,
                'formatted_amount': this._format(amount_total),
            });
            let group = this.totals.value.groups_by_subtotal[subtotal_title];
            for (let i in group) {
                amount_tax = amount_tax + group[i].tax_group_amount;
            }
        }
        this.totals.value.subtotals = subtotals;
        let amount_total = amount_untaxed + amount_tax;
        this.totals.value.amount_total = amount_total;
        this.totals.value.formatted_amount_total = this._format(amount_total);
        for (let group_name of Object.keys(this.totals.value.groups_by_subtotal)) {
            let group = this.totals.value.groups_by_subtotal[group_name];
            for (let i in group) {
                group[i].formatted_tax_group_amount = this._format(group[i].tax_group_amount);
                group[i].formatted_tax_group_base_amount = this._format(group[i].tax_group_base_amount);
            }
        }
    }
}

LegacyTaxTotalsComponent.template = 'account.LegacyTaxTotalsField';
LegacyTaxTotalsComponent.components = { LegacyTaxGroupComponent };


field_registry.add('account-tax-totals-field', LegacyTaxTotalsComponent);

export default LegacyTaxTotalsComponent
