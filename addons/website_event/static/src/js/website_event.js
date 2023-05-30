/** @odoo-module alias=website_event.website_event **/

import ajax from "web.ajax";
import core from "web.core";
import Widget from "web.Widget";
import publicWidget from "web.public.widget";

var _t = core._t;

// Catch registration form event, because of JS for attendee details
var EventRegistrationForm = Widget.extend({

    /**
     * @override
     */
    start: function () {
        var self = this;
        var res = this._super.apply(this.arguments).then(function () {
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

        // "post" looks like: { nb_register-9: "2", nb_register-10: "0" }
        const noTicketsOrdered = Object.values(post).map((value) => parseInt(value)).every(value => value === 0);
        if (noTicketsOrdered) {
            $('<div class="alert alert-info"/>')
                .text(_t('Please select at least one ticket.'))
                .insertAfter('#registration_form table');
            return new Promise(function () {});
        } else {
            $button.attr('disabled', true);
            return ajax.jsonRpc($form.attr('action'), 'call', post).then(function (modal) {
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

export default EventRegistrationForm;
