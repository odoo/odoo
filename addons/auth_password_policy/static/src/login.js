/** @odoo-module */

import publicWidget from 'web.public.widget';
import {isPasswordLeaked} from "./password_leak_check";
import {getCookie, setCookie} from "web.utils.cookies";

publicWidget.registry.login = publicWidget.Widget.extend({
    selector: '.oe_login_form',
    events: {
        'submit': '_onSubmit',
    },

    async _onSubmit(ev) {
        if (ev.isDefaultPrevented()) {
            return;
        }

        let username = this.$('input[name="login"]').val();
        let password = this.$('input[name="password"]').val();

        const cookieName = `password_leak_already_checked_${username}`;
        let cookie = getCookie(cookieName);
        if (cookie) {
            // Only run the check if the cookie is not set.
            return;
        }

        let {enabled, error, frequency_count, frequency_unit} = await this._rpc({
            route: '/login/get_password_leak_check_settings',
        });
        // Don't check anything if the user doesn't exist.
        if (error || !enabled) {
            return;
        }

        let leaked;
        try {
            leaked = await isPasswordLeaked(password);
        } catch (e) {
            return;
        }

        let ttl = checkFrequencyInSeconds(frequency_count, frequency_unit);
        setCookie(cookieName, 1, ttl);

        await this._rpc({
            route: '/login/password_leak_check_performed',
            params: {
                'username': username,
                'is_password_leaked': leaked,
            }
        });
    },
});

function checkFrequencyInSeconds(count, unit) {
    switch (unit) {
        case 'hours':
            return count * 3600;
        case 'days':
            return count * 3600 * 24;
        case 'months':
            return count * 3600 * 24 * 30;
        default:
            throw new Error(`Unknown time unit '${unit}'`);
    }
}
