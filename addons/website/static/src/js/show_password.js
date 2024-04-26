/** @odoo-module **/

//
// This file is meant to allow to switch the type of an input #password
// from password to text on mousedown on an input group.
// On mouse down, we see the password in clear text
// On mouse up, we hide it again.
//

import publicWidget from "@web/legacy/js/public/public_widget";

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
        document.body.removeEventListener(".ShowPassword");
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onShowPassword: function () {
        this.el.closest('.input-group').querySelector('#password').setAttribute('type', 'password');
    },
    /**
     * @private
     */
    _onShowText: function () {
        document.body.addEventListener('mouseup.ShowPassword', this._onShowPassword.bind(this), { once: true });
        document.body.addEventListener('touchend.ShowPassword', this._onShowPassword.bind(this), { once: true });
        this.el.closest('.input-group').querySelector('#password').setAttribute('type', 'text');
    },
});

export default publicWidget.registry.ShowPassword;
