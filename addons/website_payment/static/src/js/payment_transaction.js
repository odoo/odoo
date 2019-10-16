odoo.define('website_payment.website_payment', function (require) {
  "use strict";

var website = require('website.website');
var animation = require('web_editor.snippets.animation');
var ajax = require('web.ajax');

if(!$('.o_website_payment').length) {
  return $.Deferred().reject("DOM doesn't contain '.o_website_payment'");
}

animation.registry.payment_transaction = animation.Class.extend({
  selector: '.o_website_payment_new_payment',

  start: function () {
      this._super();
      this.$target.on("submit", "form", this.onSubmit.bind(this));
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

  createTransaction: function(data) {
    return ajax.jsonRpc('/website_payment/transaction', 'call', data);
  },

  getTxData: function() {
    var data =this.$el.data();
    data = _.pick(data, ['acquirer_id', 'amount', 'reference', 'currency_id']);
    return data;
  },

  onSubmit: function (ev) {
      ev.preventDefault();
      return this.createTransaction(this.getTxData()).then(function() {
        ev.target.submit();
      });
  },
});

return animation.registry.payment_transaction;
});

odoo.define('website_payment.payment_form', function (require) {
  "use strict";

var animation = require('web_editor.snippets.animation');
var ajax = require('web.ajax');

animation.registry.payment_form = animation.Class.extend({
  selector: 'div.row:has(div[data-acquirer-id]):not(.oe_website_contract), #payment_message',
  // DBO NOTE: this selector is complete garbage but there's nothing else I can anchor
  // myself on in the dom of the website_payment.pay_methods template -_-
  // The point here is to select the div containing the payment form in /website_payment/pay
  // and the payment alert div in the my/contract/ page without selecting anything more than that

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
  },

  createToken: function(ev, data, action_url) {
      if (data && action_url) {
          return ajax.jsonRpc(action_url, 'call', data);
      } else {
          return $.Deferred().resolve(data);
      }
  },
});

return animation.registry.payment_form;
});
