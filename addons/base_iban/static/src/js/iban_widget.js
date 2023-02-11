odoo.define('base_iban.iban_widget', function (require) {
"use strict";

var basicFields = require('web.basic_fields');
var core = require('web.core');
var fieldRegistry = require('web.field_registry');

var FieldChar = basicFields.FieldChar;

var _t = core._t;
/**
 * IbanWidget is a widget to check if the iban number is valide.
 * If the bank account is correct, it will show a green check pictogram
 * next to number, if the number is not complient with IBAN format, a
 * red cross will be show. This pictogram is computed every time the user
 * changes the field (If user is typing, there is a debouce of 400ms).
 */
var IbanWidget = FieldChar.extend({
    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this.ibanIsValid;
        this._isValid = true;
        this._compute_debounce = _.debounce(this._compute, 400);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Compute if iban is valid
     * @private
     */
    _compute: function () {
        var self = this;
        var content = this._getValue();

        if (content.length === 0) {
            this.ibanIsValid = true;
            this.$el.last().filter('.o_iban').removeClass('fa-check text-success fa-times text-danger o_iban_fail');
            this.$el.last().filter('.o_iban').attr('title', '');
        } else if (content.length < 15) {
            if (this.ibanIsValid !== false) {
                this.ibanIsValid = false;
                this._renderValid();
            }
        } else {
            this._rpc({
                model: 'res.partner.bank',
                method: 'check_iban',
                args: [[], content],
            })
            .then(function (result) {
                if (result !== self.ibanIsValid) {
                    self.ibanIsValid = result;
                    self._renderValid();
                }
            });
        }
    },
    /**
     * @private
     * @override
     * @returns {Promise|undefined}
     */
    _renderEdit: function () {
        var res = this._super.apply(this, arguments);
        this._compute();
        return res;
    },
    /**
     * Render the pictogram next to account number.
     * @private
     */
    _renderValid: function () {
        var warningMessage = _t("Account isn't IBAN compliant.");

        if (this.$el.filter('.o_iban').length === 0) {
            var $span;
            if (!this.ibanIsValid) {
                $span = $('<span class="fa fa-times o_iban text-danger o_iban_fail"/>');
                $span.attr('title', warningMessage);
            } else {
                $span = $('<span class="fa fa-check o_iban text-success"/>');
            }
            this.$el.addClass('o_iban_input_with_validator');
            $span.insertAfter(this.$el);
            this.$el = this.$el.add($span);
        }

        if (!this.ibanIsValid) {
            this.$el.last().filter('.o_iban').removeClass('fa-check text-success').addClass('fa-times text-danger o_iban_fail');
            this.$el.last().filter('.o_iban').attr('title', warningMessage);
        } else {
            this.$el.last().filter('.o_iban').removeClass('fa-times text-danger o_iban_fail').addClass('fa-check text-success');
            this.$el.last().filter('.o_iban').attr('title', '');

        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _onChange: function () {
        this._super.apply(this, arguments);
        this._compute();
    },
    /**
     * @override
     * @private
     */
    _onInput: function () {
        this._super.apply(this, arguments);
        this._compute_debounce();
    },
});

fieldRegistry.add('iban', IbanWidget);

return IbanWidget;
});
