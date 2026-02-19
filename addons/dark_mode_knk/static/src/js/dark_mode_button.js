/** @odoo-module **/

import SystrayMenu from 'web.SystrayMenu';
import Widget from 'web.Widget';
import Session from 'web.session';
import { browser } from "@web/core/browser/browser";
import { getCookie, setCookie } from "web.utils.cookies";

var ThemeWidget = Widget.extend({
    template: 'knk_dark_mode',
    events: {
        'click #dark_mode_knk': '_onClick',
    },

    is_admin: false,
    colorScheme: false,
    willStart: function () {
        this.is_admin = Session.is_admin;
        this.colorScheme = getCookie("color_scheme");
        if (this.colorScheme === 'dark') {
            $('.o_web_client').addClass('knk_night_mode');
            $('#moon_button').css("display", "none");
            $('#sun_button').css("display", "inline-flex");
        }
        else if (this.colorScheme === 'light') {
            $('.o_web_client').removeClass('knk_night_mode');
            $('#moon_button').css("display", "inline-flex");
            $('#sun_button').css("display", "none");
        } else {
            this.theme_mode = 'light';
        }
        return this._super.apply(this, arguments);
    },

    _onClick: function(env){
        var colorScheme = getCookie("color_scheme");
        const scheme = colorScheme === "dark" ? "light" : "dark";
        setCookie("color_scheme", scheme);
        this.colorScheme = scheme;
        browser.location.reload();
    },
});
SystrayMenu.Items.push(ThemeWidget);
export default ThemeWidget;
