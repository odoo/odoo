odoo.define('website_event_booth.BoothRegistrationModal', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var publicWidget = require('web.public.widget');

var _t = core._t;

var BoothRegistrationModal = Dialog.extend({
    template: 'booth.registration.details',

    init: function (parent, options) {
        this.parent = parent;
        this.eventId = parent.$el.data('event-id');
        this.csrf_token = odoo.csrf_token;
        options = _.defaults(options || {}, {
            title: _t("Registration Details"),
            technical: false,
            buttons: [
                {
                    text: _t("Cancel"),
                    classes: "btn-secondary float-left",
                    close: true,
                }
            ],
        });
        this._super(parent, options);
    },

    willStart: function () {
        let self = this;
        let params = this._serializeForm(this.parent.$el);
        return Promise.all([
            this._super.apply(this, arguments),
            this._rpc({
                route: this.parent.el.action,
                params: params,
            }).then(function (result) {
                self.name = result.details.name || '';
                self.email = result.details.email || '';
                self.phone = result.details.phone || '';
                self.mobile = result.details.mobile || '';
                self.unavailableSlots = result.unavailable_slots;
                self.requestedSlots = result.requested_slots;
                if (!self.unavailableSlots) {
                    self.buttons.unshift({
                        text: _t("Continue"),
                        classes: "btn-primary",
                        click: self._onContinueClick
                    });
                }
                self.set_buttons(self.buttons);
            })
        ]);
    },
    
    _serializeForm: function($form) {
        let result = {};
        let array = $form.serializeArray();
        $.each(array, function () {
            let value = (isNaN(this.value)) ? this.value : parseInt(this.value);
            if (result[this.name] !== undefined) {
                if (!result[this.name].push) {
                    result[this.name] = [result[this.name]];
                }
                result[this.name].push(value || '');
            } else {
                result[this.name] = value || '';
            }
        });
        return result;
    },

    _onContinueClick: function () {
        let $form = this.$('form');
        if ($form.get(0).reportValidity()) {
            $form.submit();
        }
    },
});

publicWidget.registry.boothRegistrationModalInstance = publicWidget.Widget.extend({
    selector: '#booth-registration',
    xmlDependencies: ['/website_event_booth/static/src/xml/templates.xml'],
    events: {
        'click .booth-submit': '_onSubmitClick'
    },

    _onSubmitClick: function (ev) {
        ev.preventDefault();
        new BoothRegistrationModal(this).open();
    },
});

return BoothRegistrationModal;

});
