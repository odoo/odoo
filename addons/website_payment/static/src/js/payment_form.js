odoo.define('website_payment.payment_form', function (require) {
    "use strict";

var animation = require('web_editor.snippets.animation');

animation.registry.payment_form = animation.Class.extend({
    selector: '.o_payment_form, #payment_message',

    start: function () {
        this._super();
        this.$target.on("submit", "form", this.onSubmit.bind(this));
        this.$target.on("change", 'select[name="pm_acquirer_id"]', this.updateNewPaymentDisplayStatus.bind(this));
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
            acquirer_id = this.$('.acquirer').data().acquirerId;
        }
        $('.acquirer').addClass('hidden');
        $('.acquirer[data-acquirer-id="'+acquirer_id+'"]').removeClass('hidden');
    },

    onSubmit: function (ev) {
        ev.preventDefault();
        ev.target.submit();
    }
});

return animation.registry.payment_form;
});
