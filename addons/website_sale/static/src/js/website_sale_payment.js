odoo.define('website_sale.payment', function (require) {
"use strict";

var ajax = require('web.ajax');

var animation = require('web_editor.snippets.animation');
var ajax = require('web.ajax');


animation.registry.website_sale_payment = animation.Class.extend({
  selector: '.oe_website_sale #payment_method',

  start: function() {
    var self = this;
    this._super();
    this.$target.on("click", "input[name='acquirer'], a.btn_payment_token", this.switchAcquirer.bind(this)).find("input[name='acquirer']:checked").click();
    this.$target.on("submit", this.makePayment.bind(this));
    if (this.$("#checkbox_cgv").length) {
      this.$("#checkbox_cgv").on('change',function() {
        self.$("div.oe_sale_acquirer_button").find('input, button').prop("disabled", !this.checked);
      });
      this.$('#checkbox_cgv').trigger('change');
    }
  },

  switchAcquirer: function(ev) {
    var ico_off = 'fa-circle-o';
    var ico_on = 'fa-dot-circle-o';

    var payment_id = $(ev.currentTarget).val() || $(ev.currentTarget).data('acquirer');
    var token = $(ev.currentTarget).data('token') || '';

    $("div.oe_sale_acquirer_button[data-id='"+payment_id+"']", this.$target).attr('data-token', token);
    $("div.js_payment a.list-group-item").removeClass("list-group-item-info");
    $('span.js_radio').switchClass(ico_on, ico_off, 0);
    if (token) {
      $("div.oe_sale_acquirer_button div.token_hide").hide();
      $(ev.currentTarget).find('span.js_radio').switchClass(ico_off, ico_on, 0);
      $(ev.currentTarget).parents('li').find('input').prop("checked", true);
      $(ev.currentTarget).addClass("list-group-item-info");
    }
    else{
      $("div.oe_sale_acquirer_button div.token_hide").show();
    }
    $("div.oe_sale_acquirer_button[data-id]", this.$target).addClass("hidden");
    $("div.oe_sale_acquirer_button[data-id='"+payment_id+"']", this.$target).removeClass("hidden");
  },

  makePayment: function(ev) {
    ev.preventDefault();
    ev.stopPropagation();
    var self = this;
    var $form = $(ev.target);
    var acquirer = this.$('div.oe_sale_acquirer_button:visible').first();
    var acquirer_id = acquirer.data('id');
    var acquirer_token = acquirer.data('token'); // !=data
    var params = {'tx_type': acquirer.find('input[name="odoo_save_token"]').is(':checked')?'form_save':'form'};
    if (! acquirer_id) {
      return false;
    }
    if (acquirer_token) {
      params.token = acquirer_token;
    }
    $form.off('submit');
    ajax.jsonRpc('/shop/payment/transaction/' + acquirer_id, 'call', params).then(function (data) {
      self.postProcessTx(data, acquirer_id);
    });
    return false;
  },

  postProcessTx: function(data, acquirer_id) {
    $(data).appendTo('body').submit();
  }

});

animation.registry.website_sale_payment_token = animation.Class.extend({
    selector: '.oe_website_sale .oe_pay_token',

    start: function () {
        var self = this;
        this._super();
        this.$target.on('click', 'a.js_btn_valid_tx', function () {
            $('div.js_token_load').toggle();
            var $form = $(this).parents('form');
            ajax.jsonRpc($form.attr('action'), 'call', $.deparam($form.serialize())).then(function (data) {
                if (data.url) {
                    window.location = data.url;
                } else {
                    $('div.js_token_load').toggle();
                    if (!data.success && data.error) {
                        $('div.oe_pay_token div.panel-body p').html(data.error + '<br/><br/>' + _('Retry ? '));
                        $('div.oe_pay_token div.panel-body')
                            .parents('div')
                            .removeClass('panel-info')
                            .addClass('panel-danger');
                    }
                }
            });
        });
    },
});

return animation.registry.website_sale_payment;
});
