/** @odoo-module **/

import publicWidget from 'web.public.widget';

publicWidget.registry.o_plausible_push = publicWidget.Widget.extend({
    selector: '.js_plausible_push',

    /**
     * @override
     */
    start() {
        window.plausible = window.plausible || function () {
            (window.plausible.q = window.plausible.q || []).push(arguments);
        };
        this._push();
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Pushes the event `data-event-name` to Plausible with params
     * `data-event-params`
     */
    _push() {
        const evName = this.$el.data('event-name').toString();
        const evParams = this.$el.data('event-params') || {};
        window.plausible(evName, {props: evParams});
    },
});
