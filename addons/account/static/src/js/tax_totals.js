/** @odoo-module alias=account.tax_group_owl **/
"use strict";

const { Component } = owl;
const { useState, useRef } = owl.hooks;
import session from 'web.session';
import AbstractFieldOwl from 'web.AbstractFieldOwl';
import fieldUtils from 'web.field_utils';
import field_registry from 'web.field_registry_owl';

/**
    A line of some TaxTotalsComponent, giving the values of a tax group.
**/
class TaxGroupComponent extends Component {

    constructor(parent, props) {
        super(parent, props);
        this.inputTax = useRef('taxValueInput');
        this.state = useState({value: 'readonly'});
        this.allowTaxEdition = this.__owl__.parent.mode === 'edit' ? props.allowTaxEdition : false;
    }

    //--------------------------------------------------------------------------
    // Life cycle methods
    //--------------------------------------------------------------------------

    willUpdateProps(nextProps) {
        this.setState('readonly'); // If props are edited, we set the state to readonly
    }

    patched() {
        if (this.state.value === 'edit') {
            this.inputTax.el.focus(); // Focus the input
            this.inputTax.el.value = this.props.taxGroup.tax_group_amount;
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
        } catch (err) {
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
        this.trigger('change-tax-group', {
            oldValue: this.props.taxGroup.tax_group_amount,
            newValue: newValue,
            taxGroupId: this.props.taxGroup.tax_group_id
        });
    }
}
TaxGroupComponent.props = ['taxGroup', 'allowTaxEdition', 'record'];
TaxGroupComponent.template = 'account.TaxGroupComponent';

/**
    Widget used to display tax totals by tax groups for invoices, PO and SO,
    and possibly allowing editing them.

    Note that this widget requires the object it is used on to have a
    currency_id field.
**/
class TaxTotalsComponent extends AbstractFieldOwl {
    constructor(...args) {
        super(...args);
        this.totals = useState({value: this.value ? JSON.parse(this.value) : null});
        this.allowTaxEdition = this.nodeOptions['allowTaxEdition'];
    }

    willUpdateProps(nextProps) {
        // We only reformat tax groups if there are changed
        this.totals.value = JSON.parse(nextProps.record.data[this.props.fieldName]);
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
     * It is called by an event trigger (from the TaxGroupComponent) and receives
     * a particular payload.
     *
     * It is responsible for calculating taxes based on tax groups and triggering
     * an event to notify the ORM of a change.
     */
    _onChangeTaxValueByTaxGroup(ev) {
        this.trigger('field-changed', {
            dataPointID: this.record.id,
            changes: { tax_totals_json: JSON.stringify(this.totals.value) }
        })
    }
}

TaxTotalsComponent.template = 'account.TaxTotalsField';
TaxTotalsComponent.components = { TaxGroupComponent };


field_registry.add('account-tax-totals-field', TaxTotalsComponent);

export default TaxTotalsComponent
