odoo.define('website_payment.payment_form', function (require) {
    "use strict";

var ajax = require('web.ajax');
var animation = require('web_editor.snippets.animation');

animation.registry.payment_form = animation.Class.extend({
    selector: '.o_payment_form, #payment_message, .oe_pay_token',

    start: function () {
        this._super();
        this.$target.on("submit", "form", this.onSubmit.bind(this));
        this.$target.on("change", 'select[name="pm_acquirer_id"]', this.updateNewPaymentDisplayStatus.bind(this));
        this.$target.on("click", '.js_btn_valid_tx', this._chargePaymentToken.bind(this));
    },

    disableButton: function (button) {
        $(button).attr('disabled', true);
        $(button).children('.fa-lock').removeClass('fa-lock');
        $(button).prepend('<span class="o_loader"><i class="fa fa-refresh fa-spin"></i>&nbsp;</span>');
    },

    enableButton: function (button) {
        $(button).attr('disabled', false);
        $(button).children('.fa').addClass('fa-lock');
        $(button).find('span.o_loader').remove();
    },

    /**
     * @private
     * @param {jQuery} $form
     */
    getFormData: function ($form) {
        var unindexed_array = $form.serializeArray();
        var indexed_array = {};

        $.map(unindexed_array, function (n, i) {
            indexed_array[n.name] = n.value;
        });
        return indexed_array;
    },

    updateNewPaymentDisplayStatus: function (ev) {
        var acquirer_id = this.$('select[name="pm_acquirer_id"] :selected').val();
        if (!acquirer_id) {
            acquirer_id = this.$('.acquirer').data() && this.$('.acquirer').data().acquirerId;
        }
        $('.acquirer').addClass('hidden');
        $('.acquirer[data-acquirer-id="'+acquirer_id+'"]').removeClass('hidden');
    },

    onSubmit: function (ev) {
        ev.preventDefault();
        ev.target.submit();
    },
    _chargePaymentToken: function (ev) {
        this.$('div.js_token_load').toggle();

        var $form = this.$('form');

        ajax.jsonRpc($form.attr('action'), 'call', $.deparam($form.serialize())).then(function (data) {
            if (data.url) {
              window.location = data.url;
            } else {
              $('div.js_token_load').toggle();
              if (!data.success && data.error) {
                $('div.oe_pay_token div.panel-body p').html(data.error + "<br/><br/>" + _('Retry ? '));
                $('div.oe_pay_token div.panel-body').parents('div').removeClass('panel-info').addClass('panel-danger');
              }
            }
        });
    }
});

return animation.registry.payment_form;
});
