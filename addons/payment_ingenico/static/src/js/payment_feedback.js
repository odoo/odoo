odoo.define('payment_ingenico.payment_feedback', function (require) {

    "use strict";
    var ajax = require('web.ajax');
    var core = require('web.core');
    var publicWidget = require('web.public.widget');
    var _t = core._t;
    var qweb = core.qweb;
    var csrf_value = require('web.core').csrf_token

    publicWidget.registry.ogoneFeedback = publicWidget.Widget.extend({
        selector: '.o_payment_feedback',
        start: function () {
            this.feedback();
        },

        feedback: function() {
            var action_url = this.$el.data('json-route');
            var form_data = this.$el.data('form');
            console.log(form_data)
            var self = this;
            var odooForm = document.createElement("form");
            odooForm.method = "POST";
            odooForm.action = action_url;
            var el = document.createElement("input");
            el.setAttribute('type', 'submit');
            el.setAttribute('name', "Submit");
            var csrf_el = document.createElement("input");
            csrf_el.setAttribute('type', 'hidden');
            csrf_el.setAttribute('name', "csrf_token");
            csrf_el.setAttribute('value', csrf_value);
            odooForm.appendChild(csrf_el);
            _.each(form_data, function (value, key) {
                var el = document.createElement("input");
                el.setAttribute('type', 'hidden');
                el.setAttribute('value', value);
                el.setAttribute('name', key);
                odooForm.appendChild(el);
            });
            document.body.appendChild(odooForm);;
            odooForm.submit();
            },
    });
});
