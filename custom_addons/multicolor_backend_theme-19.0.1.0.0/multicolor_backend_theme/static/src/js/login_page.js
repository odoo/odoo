/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.loginPage = publicWidget.Widget.extend({
    selector: '.oe_login_buttons',
    async start() {
        var data = await rpc('/active_theme')
        if (data) {
            this.$('.cybro-login-btn').css({
                    'background-color': data.theme_main_color,
                    'color': data.theme_font_color
                });
            this.$('.cybro-super-btn').css({
                    'color': data.view_font_color
                });
        }
    }
})