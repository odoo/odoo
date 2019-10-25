//
// This file is meant to determine the timezone of a website visitor
// If the visitor already exists, no need to keep the timezone cookie
// as the timezone is set on the visitor.
//
odoo.define('website.show_password', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.ShowPassword = publicWidget.Widget.extend({
    selector: '#showPass',
    events: {
        'mousedown': '_onShowText',
        'touchstart': '_onShowText',
    },

    /**
     * @override
     */
    destroy: function () {
        this._super(...arguments);
        $('body').off(".ShowPassword");
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onShowPassword: function () {
        this.$el.closest('.input-group').find('#password').attr('type', 'password');
    },
    /**
     * @private
     */
    _onShowText: function () {
        $('body').one('mouseup.ShowPassword touchend.ShowPassword', this._onShowPassword.bind(this));
        this.$el.closest('.input-group').find('#password').attr('type', 'text');
    },
});

return publicWidget.registry.ShowPassword;

});
