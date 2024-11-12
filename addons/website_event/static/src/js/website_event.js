odoo.define('website_event.website_event', function (require) {

var ajax = require('web.ajax');
var core = require('web.core');
var Widget = require('web.Widget');
var publicWidget = require('web.public.widget');
var {ReCaptcha} = require('google_recaptcha.ReCaptchaV3');

var _t = core._t;

// Catch registration form event, because of JS for attendee details
var EventRegistrationForm = Widget.extend({

    /**
     * @constructor
     */
    init: function () {
        this._super(...arguments);
        this._recaptcha = new ReCaptcha();
    },

    /**
     * @override
     */
    willStart: async function () {
        this._recaptcha.loadLibs();
        return this._super(...arguments);
    },

    /**
     * @override
     */
    start: function () {
        var self = this;
        var res = this._super.apply(this, arguments).then(function () {
            $('#registration_form .a-submit')
                .off('click')
                .click(function (ev) {
                    self.on_click(ev);
                })
                .prop('disabled', false);
        });
        return res;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    on_click: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var $form = $(ev.currentTarget).closest('form');
        var $button = $(ev.currentTarget).closest('[type="submit"]');
        var post = {};
        $('#registration_form table').siblings('.alert').remove();
        $('#registration_form select').each(function () {
            post[$(this).attr('name')] = $(this).val();
        });
        var tickets_ordered = _.some(_.map(post, function (value, key) { return parseInt(value); }));
        if (!tickets_ordered) {
            $('<div class="alert alert-info"/>')
                .text(_t('Please select at least one ticket.'))
                .insertAfter('#registration_form table');
            return new Promise(function () {});
        } else {
            $button.attr('disabled', true);
            var action = $form.data('action') || $form.attr('action');
            var self = this;
            return ajax.jsonRpc(action, 'call', post).then(async function (modal) {
                const tokenObj = await self._recaptcha.getToken('website_event_registration');
                if (tokenObj.error) {
                    self.displayNotification({
                        type: 'danger',
                        title: _t('Error'),
                        message: tokenObj.error,
                        sticky: true,
                    });
                    $button.prop('disabled', false);
                    return false;
                }
                var $modal = $(modal);
                $modal.find('.modal-body > div').removeClass('container'); // retrocompatibility - REMOVE ME in master / saas-19
                $modal.appendTo(document.body);
                const modalBS = new Modal($modal[0], {backdrop: 'static', keyboard: false});
                modalBS.show();
                $modal.appendTo('body').modal('show');
                $modal.on('click', '.js_goto_event', function () {
                    $modal.modal('hide');
                    $button.prop('disabled', false);
                });
                $modal.on('click', '.btn-close', function () {
                    $button.prop('disabled', false);
                });
                $modal.on('submit', 'form', function (ev) {
                    const tokenInput = document.createElement('input');
                    tokenInput.setAttribute('name', 'recaptcha_token_response');
                    tokenInput.setAttribute('type', 'hidden');
                    tokenInput.setAttribute('value', tokenObj.token);
                    ev.currentTarget.appendChild(tokenInput);
                })
            });
        }
    },
});

publicWidget.registry.EventRegistrationFormInstance = publicWidget.Widget.extend({
    selector: '#registration_form',

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        this.instance = new EventRegistrationForm(this);
        return Promise.all([def, this.instance.attachTo(this.$el)]);
    },
    /**
     * @override
     */
    destroy: function () {
        this.instance.setElement(null);
        this._super.apply(this, arguments);
        this.instance.setElement(this.$el);
    },
});

return EventRegistrationForm;
});
