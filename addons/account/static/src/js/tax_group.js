/** @odoo-module alias=account.tax_group_owl **/
"use strict";

const { Component } = owl;
const { useState, useRef } = owl.hooks;
import session from 'web.session';
import AbstractFieldOwl from 'web.AbstractFieldOwl';
import fieldUtils from 'web.field_utils';
import field_registry from 'web.field_registry_owl';

class TaxGroupComponent extends Component {
    constructor(parent, props) {
        super(parent, props);
        this.inputTax = useRef('taxValueInput');
        this.state = useState({value: 'readonly'});
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
        let currency = session.get_currency(this.props.record.data.currency_id.data.id);
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
        this.trigger('change-tax-group', {
            oldValue: this.props.taxGroup.tax_group_amount,
            newValue: newValue,
            taxGroupId: this.props.taxGroup.tax_group_id
        });
    }
}
TaxGroupComponent.props = ['taxGroup', 'displayEditWidget', 'record'];
TaxGroupComponent.template = 'account.TaxGroupComponent';

class TaxGroupListComponent extends AbstractFieldOwl {
    constructor(...args) {
        super(...args);
        this.taxGroups = useState({value: JSON.parse(this.value)});
        this.displayEditWidget = this._displayEditWidget();
    }

    //--------------------------------------------------------------------------
    // Life cycle method
    //--------------------------------------------------------------------------

    willUpdateProps(nextProps) {
        // We only reformat tax groups if there are changed
        if (nextProps.fieldName === 'amount_by_group') {
            this.taxGroups.value = JSON.parse(this.value);
        }
    }

    //--------------------------------------------------------------------------
    // Events
    //--------------------------------------------------------------------------

    _onKeydown(ev) {
        switch (ev.which) {
            // Trigger only if the user clicks on ENTER or on TAB.
            case $.ui.keyCode.ENTER:
            case $.ui.keyCode.TAB:
                // trigger blur to prevent the code being executed twice
                $(ev.target).blur();
        }
    }

    //--------------------------------------------------------------------------
    // Private methods
    //--------------------------------------------------------------------------

    /**
     * Tricky method to get the parentWidget. It necessary to do that because
     * we need to know the view mode. (If we are in readonly or edit).
     */
    _getParentWidget() {
        return this.__owl__.parent.parentWidget;
    }

    /**
     * This method checks that the document where the widget
     * is located is of the "in_invoice" or "in_refund" type.
     * This makes it possible to know if it is a purchase
     * document.
     *
     * @returns boolean (true if the invoice is a purchase document)
     */
    _isPurchaseDocument() {
        let purchaseMoveTypes = ['in_invoice', 'in_refund'];
        return purchaseMoveTypes.includes(this.record.data.move_type)
    }

    /**
     * This method verifies that the account move is a purchase document, that the document is in draft and
     * that the edit mode is enabled.
     */
    _displayEditWidget() {
        return this._isPurchaseDocument() && this.record.data.state === 'draft' && this._getParentWidget().mode === 'edit';
    }

    /**
     * This method is the main function of the tax group widget.
     * It is called by an event trigger (from the TaxGroupComponent) and receives
     * a particular payload.
     *
     * It is responsible for calculating taxes based on tax groups and triggering
     * an event to notify the ORM of a change.
     *
     * @param {*} ev
     * @param {*} ev.details A payload with the tax group id, the old value of the
     * tax group and the new value.
     */
    _onChangeTaxValueByTaxGroup(ev) {
        let detail = ev.detail;
        this.taxGroups.value.forEach(taxGroup => {
           if (taxGroup.tax_group_id === detail.taxGroupId) {
               taxGroup.tax_group_amount = detail.newValue;
           }
        });
        this.trigger('field-changed', {
            dataPointID: this.record.id,
            changes: { amount_by_group: JSON.stringify(this.taxGroups.value) }
        })
    }
}
TaxGroupListComponent.template = 'account.TaxGroupCustomField';
TaxGroupListComponent.components = { TaxGroupComponent };

field_registry.add('tax-group-custom-field', TaxGroupListComponent);

export default TaxGroupListComponent
