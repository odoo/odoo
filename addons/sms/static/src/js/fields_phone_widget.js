odoo.define('sms.fields', function (require) {
"use strict";

var basic_fields = require('web.basic_fields');
var core = require('web.core');
var session = require('web.session');

var _t = core._t;

/**
 * Override of FieldPhone to use add a button calling SMS composer if option activated
 */

var Phone = basic_fields.FieldPhone;
Phone.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Open SMS composer wizard
     *
     * @private
     */
    _onClickSMS: function (ev) {
        ev.preventDefault();

        var context = session.user_context;
        context = _.extend({}, context, {
            default_res_model: this.model,
            default_res_id: parseInt(this.res_id),
            default_number_field_name: this.name,
            default_composition_mode: 'comment',
        });
        var self = this;
        return this.do_action({
            title: _t('Send SMS Text Message'),
            type: 'ir.actions.act_window',
            res_model: 'sms.composer',
            target: 'new',
            views: [[false, 'form']],
            context: context,
        }, {
        on_close: function () {
            self.trigger_up('reload');
        }});
    },

    /**
     * Add a button to call the composer wizard
     *
     * @override
     * @private
     */
    _renderReadonly: function () {
        var def = this._super.apply(this, arguments);
        if (this.nodeOptions.enable_sms) {
            var $composerButton = $('<a>', {
                title: _t('Send SMS Text Message'),
                href: '',
                class: 'ml-3 d-inline-flex align-items-center o_field_phone_sms',
                html: $('<small>', {class: 'font-weight-bold ml-1', html: 'SMS'}),
            });
            $composerButton.prepend($('<i>', {class: 'fa fa-mobile'}));
            $composerButton.on('click', this._onClickSMS.bind(this));
            this.$el = $('<div/>').append(this.$el).append($composerButton);
        }

        return def;
    },
});

return Phone;

});
