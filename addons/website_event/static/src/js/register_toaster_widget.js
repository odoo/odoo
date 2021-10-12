odoo.define('website_event.register_toaster_widget', function (require) {
'use strict';

let core = require('web.core');
const {Markup} = require('web.utils');
let _t = core._t;
let publicWidget = require('web.public.widget');

publicWidget.registry.RegisterToasterWidget = publicWidget.Widget.extend({
    selector: '.o_wevent_register_toaster',

    /**
     * This widget allows to display a toast message on the page.
     *
     * @override
     */
    start: function () {
        const message = this.$el.data('message');
        if (message && message.length) {
            this.displayNotification({
                title: _t("Register"),
                message: Markup(message),
                type: 'info',
            });
        }
        return this._super.apply(this, arguments);
    },
});

return publicWidget.registry.RegisterToasterWidget;

});
