import publicWidget from '@web/legacy/js/public/public_widget';
import { deserializeDateTime } from "@web/core/l10n/dates";

export function processDataset(data) {
    if (data instanceof DOMStringMap) {
        data = Object.assign({}, data);
    }
    const rbrace = /^(?:\{[\w\W]*\}|\[[\w\W]*\])$/;
    for (const [key, value] of Object.entries(data)) {
        if (value === "true" || value === "True") {
            data[key] = true;
        }
        if (value === "false" || value === "False") {
            data[key] = false;
        }
        if (value === "null") {
            data[key] = null;
        }
        // Only convert to a number if it doesn't change the string
        if (value === +value + "") {
            data[key] = +value;
        }
        if (rbrace.test(value)) {
            data[key] = JSON.parse(value);
        }
    }
    return data;
}

publicWidget.registry.websiteSlides = publicWidget.Widget.extend({
    selector: '#wrapwrap',

    /**
     * @override
     * @param {Object} parent
     */
    start: function (parent) {
        var defs = [this._super.apply(this, arguments)];

        [...this.el.querySelectorAll("timeago.timeago")].forEach((el) => {
            const datetime = el.getAttribute("datetime");
            var datetimeObj = deserializeDateTime(datetime);
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
