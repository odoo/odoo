odoo.define('account.tax_group', function (require) {
    "use strict";

    const AbstractFieldOwl = require('web.AbstractFieldOwl');
    const fieldRegistry = require('web.field_registry_owl');
    const fieldUtils = require('web.field_utils');
    const patchMixin = require('web.patchMixin');

    const { useState, onPatched } = owl.hooks;

    class TaxGroupCustomField extends AbstractFieldOwl {

        constructor() {
            super(...arguments);
            this.state = useState({ shouldDisplayEdit: false });
            onPatched(this.focusInput);
        }

        focusInput() {
            const taxGroupElement = this.el.querySelector('.oe_tax_group_editable');
            if (taxGroupElement.querySelector('.tax_group_edit_input')) {
                const input = taxGroupElement.querySelector('.tax_group_edit_input input');
                input.focus(); // Focus the input
            }
        }

        //----------------------------------------------------------------------
        // Getters
        //----------------------------------------------------------------------

        get displayEditWidget() {
            const parent = this.__owl__.parent.parentWidget;
            return this._isPurchaseDocument() && this.record.data.state !== 'posted' && parent.mode === 'edit';
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * This method is called by "_setTaxGroups". It is 
         * responsible for calculating taxes based on
         * tax groups and triggering an event to
         * notify the ORM of a change.
         * 
         * @param {Id} taxGroupId
         * @param {Float} deltaAmount
         */
        _changeTaxValueByTaxGroup(taxGroupId, deltaAmount) {
            // Search for the first tax line with the same tax group and modify its value
            const lineID = this.record.data.line_ids.data.find(elem => elem.data.tax_group_id && elem.data.tax_group_id.data.id === taxGroupId);

            let debitAmount = 0;
            let creditAmount = 0;
            let amountCurrency = 0;
            if (lineID.data.currency_id) { // If multi currency enable
                if (this.record.data.move_type === "in_invoice") {
                    amountCurrency = lineID.data.amount_currency - deltaAmount;
                } else {
                    amountCurrency = lineID.data.amount_currency + deltaAmount;
                }
            } else {
                let balance = lineID.data.price_subtotal;
                balance -= deltaAmount;
                if (this.record.data.move_type === "in_invoice") { // For vendor bill
                    if (balance > 0) {
                        debitAmount = balance;
                    } else if (balance < 0) {
                        creditAmount = -balance;
                    }
                } else { // For refund
                    if (balance > 0) {
                        creditAmount = balance;
                    } else if (balance < 0) {
                        debitAmount = -balance;
                    }
                }
            }
            // Trigger ORM
            this.trigger('field_changed', {
                dataPointID: this.record.id,
                changes: { line_ids: { operation: "UPDATE", id: lineID.id, data: { amount_currency: amountCurrency, debit: debitAmount, credit: creditAmount } } }, // account.move change
                initialEvent: { dataPointID: lineID.id, changes: { amount_currency: amountCurrency, debit: debitAmount, credit: creditAmount }, }, // account.move.line change
            });
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
            return this.record.data.move_type === "in_invoice" || this.record.data.move_type === 'in_refund';
        }

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * This method is called when the user is in edit mode and 
         * leaves the <input> field. Then, we execute the code that 
         * modifies the information.
         * 
         * @param {event} ev 
         */
        _onBlur(ev) {
            const input = ev.target;
            let newValue = input.value;
            const currency = this.env.session.get_currency(this.record.data.currency_id.data.id);
            try {
                newValue = fieldUtils.parse.float(newValue);    // Need a float for format the value.             
                newValue = fieldUtils.format.float(newValue, null, { digits: currency.digits }); // return a string rounded to currency precision
                newValue = fieldUtils.parse.float(newValue); // convert back to Float to compare with oldValue to know if value has changed
            } catch (err) {
                input.classList.add('o_field_invalid');
                return;
            }
            let oldValue = input.getAttribute('data-original-value');
            oldValue = fieldUtils.parse.float(oldValue);
            if (newValue === oldValue || newValue === 0) {
                // hide input and show previous element
                this.state.shouldDisplayEdit = !this.state.shouldDisplayEdit;
                return;
            }
            let taxGroupId = this.el.querySelector('.oe_tax_group_editable');
            taxGroupId = parseInt(taxGroupId.getAttribute("data-tax-group-id"));
            this._changeTaxValueByTaxGroup(taxGroupId, oldValue - newValue);
        }

        /**
         * This method is called when the user clicks on a specific <td>.
         * it will hide the edit button and display the field to be edited.
         *
         * @param {event} ev
         */
        _onClick(ev) {
            // Show input and hide previous element
            this.state.shouldDisplayEdit = !this.state.shouldDisplayEdit;
            const taxGroupElement = this.el.querySelector('.oe_tax_group_editable');
            const input = taxGroupElement.querySelector('.tax_group_edit_input input');
            // Get original value and display it in user locale in the input
            const originalValue = fieldUtils.parse.float(input.getAttribute('data-original-value'));
            const formatedOriginalValue = fieldUtils.format.float(originalValue, {}, {});
            input.value = formatedOriginalValue; //add value in user locale to the input
        }

        /**
         * This method is called when the user is in edit mode and pressing
         * a key on his keyboard. If this key corresponds to ENTER or TAB,
         * the code that modifies the information is executed.
         *
         * @param {event} ev
         */
        _onKeydown(ev) {
            switch (ev.which) {
                // Trigger only if the user clicks on ENTER or on TAB.
                case $.ui.keyCode.ENTER:
                case $.ui.keyCode.TAB:
                    // trigger blur to prevent the code being executed twice
                    ev.target.dispatchEvent(new Event('blur'));
            }
        }
    }

    TaxGroupCustomField.template = 'AccountTaxGroupTemplate';

    fieldRegistry.add('tax-group-custom-field', patchMixin(TaxGroupCustomField));
});
