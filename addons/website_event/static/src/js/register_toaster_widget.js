/** @odoo-module alias=website_event.register_toaster_widget **/

import core from "web.core";
import {Markup} from "web.utils";
let _t = core._t;
import publicWidget from "web.public.widget";

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

export default publicWidget.registry.RegisterToasterWidget;
