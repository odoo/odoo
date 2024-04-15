/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { deserializeDateTime } from "@web/core/l10n/dates";

publicWidget.registry.websiteSlides = publicWidget.Widget.extend({
    selector: '#wrapwrap',

    /**
     * @override
     * @param {Object} parent
     */
    start: function (parent) {
        const defs = [this._super.apply(this, arguments)];

        [...this.el.querySelectorAll('timeago.timeago')].forEach((el) => {
            const datetime = el.getAttribute('datetime');
            const datetimeObj = deserializeDateTime(datetime);
            // if presentation 7 days, 24 hours, 60 min, 60 second, 1000 millis old(one week)
            // then return fix formate string else timeago
            var displayStr = '';
            if (datetimeObj && new Date().getTime() - datetimeObj.valueOf() > 7 * 24 * 60 * 60 * 1000) {
                displayStr = datetimeObj.toFormat('DD');
            } else {
                displayStr = datetimeObj.toRelative();
            }
            el.textContent = displayStr;
        });

        return Promise.all(defs);
    },
});

export default publicWidget.registry.websiteSlides;
