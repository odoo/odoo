odoo.define('account.tax_group', function (require) {
    "use strict";

    var core = require('web.core');
    var session = require('web.session');
    var fieldRegistry = require('web.field_registry');
    var AbstractField = require('web.AbstractField');
    var fieldUtils = require('web.field_utils');
    var QWeb = core.qweb;

    var TaxGroupCustomField = AbstractField.extend({
        events: {
            'click .tax_group_edit': '_onClick',
            'keydown .oe_tax_group_editable .tax_group_edit_input input': '_onKeydown',
            'blur .oe_tax_group_editable .tax_group_edit_input input': '_onBlur',
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * This method is called by "_setTaxGroups". It is 
         * responsible for calculating taxes based on
         * tax groups and triggering an event to
         * notify the ORM of a change.
         * 
         * @param {Id} taxGroupId
         * @param {Float} deltaAmount
         */
        _changeTaxValueByTaxGroup: function (taxGroupId, deltaAmount) {
            var self = this;
            // Search for the first tax line with the same tax group and modify its value
            var line_id = self.record.data.line_ids.data.find(elem => elem.data.tax_group_id && elem.data.tax_group_id.data.id === taxGroupId);

            var debitAmount = 0;
            var creditAmount = 0;
            var amount_currency = 0;
            if (line_id.data.currency_id) { // If multi currency enable
                if (this.record.data.move_type === "in_invoice") {
                    amount_currency = line_id.data.amount_currency - deltaAmount;
                } else {
                    amount_currency = line_id.data.amount_currency + deltaAmount;
                }
            } else {
                var balance = line_id.data.price_subtotal;
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
            self.trigger_up('field_changed', {
                dataPointID: self.record.id,
                changes: { line_ids: { operation: "UPDATE", id: line_id.id, data: { amount_currency: amount_currency, debit: debitAmount, credit: creditAmount } } }, // account.move change
                initialEvent: { dataPointID: line_id.id, changes: { amount_currency: amount_currency, debit: debitAmount, credit: creditAmount }, }, // account.move.line change
            });
        },

        /**
         * This method checks that the document where the widget
         * is located is of the "in_invoice" or "in_refund" type.
         * This makes it possible to know if it is a purchase
         * document.
         * 
         * @returns boolean (true if the invoice is a purchase document)
         */
        _isPurchaseDocument: function () {
            return this.record.data.move_type === "in_invoice" || this.record.data.move_type === 'in_refund';
        },

        /**
         * This method is part of the widget life cycle and allows you to render 
         * the widget.
         * 
         * @private
         * @override 
         */
        _render: function () {
            var self = this;
            // Display the pencil and allow the event to click and edit only on purchase that are not posted and in edit mode.
            // since the field is readonly its mode will always be readonly. Therefore we have to use a trick by checking the 
            // formRenderer (the parent) and check if it is in edit in order to know the correct mode.
            var displayEditWidget = self._isPurchaseDocument() && this.record.data.state === 'draft' && this.getParent().mode === 'edit';
            this.$el.html($(QWeb.render('AccountTaxGroupTemplate', {
                lines: self.value,
                displayEditWidget: displayEditWidget,
            })));
        },

        //--------------------------------------------------------------------------
        // Handler
        //--------------------------------------------------------------------------

        /**
         * This method is called when the user is in edit mode and 
         * leaves the <input> field. Then, we execute the code that 
         * modifies the information.
         * 
         * @param {event} ev 
         */
        _onBlur: function (ev) {
            ev.preventDefault();
            var $input = $(ev.target);
            var newValue = $input.val();
            var currency = session.get_currency(this.record.data.currency_id.data.id);
            try {
                newValue = fieldUtils.parse.float(newValue);    // Need a float for format the value.             
                newValue = fieldUtils.format.float(newValue, null, {digits: currency.digits}); // return a string rounded to currency precision
                newValue = fieldUtils.parse.float(newValue); // convert back to Float to compare with oldValue to know if value has changed
            } catch (err) {
                $input.addClass('o_field_invalid');
                return;
            }
            var oldValue = $input.data('originalValue');
            if (newValue === oldValue || newValue === 0) {
                return this._render();
            }
            var taxGroupId = $input.parents('.oe_tax_group_editable').data('taxGroupId');
            this._changeTaxValueByTaxGroup(taxGroupId, oldValue-newValue);
        },

        /**
         * This method is called when the user clicks on a specific <td>.
         * it will hide the edit button and display the field to be edited.
         * 
         * @param {event} ev 
         */
        _onClick: function (ev) {
            ev.preventDefault();
            var $taxGroupElement = $(ev.target).parents('.oe_tax_group_editable');
            // Show input and hide previous element
            $taxGroupElement.find('.tax_group_edit').addClass('d-none');
            $taxGroupElement.find('.tax_group_edit_input').removeClass('d-none');
            var $input = $taxGroupElement.find('.tax_group_edit_input input');
            // Get original value and display it in user locale in the input
            var formatedOriginalValue = fieldUtils.format.float($input.data('originalValue'), {}, {});
            $input.focus(); // Focus the input
            $input.val(formatedOriginalValue); //add value in user locale to the input
        },

        /**
         * This method is called when the user is in edit mode and pressing 
         * a key on his keyboard. If this key corresponds to ENTER or TAB, 
         * the code that modifies the information is executed.
         * 
         * @param {event} ev 
         */
        _onKeydown: function (ev) {
            switch (ev.which) {
                // Trigger only if the user clicks on ENTER or on TAB.
                case $.ui.keyCode.ENTER:
                case $.ui.keyCode.TAB:
                    // trigger blur to prevent the code being executed twice
                    $(ev.target).blur();
            }
        },

    });
    fieldRegistry.add('tax-group-custom-field', TaxGroupCustomField)
});
