/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.EventTimezoneConverter = publicWidget.Widget.extend({
    selector: '.o_event_tz_converter',
    events: {
        'change select[name="timezone"]': '_onTimezoneChange',
    },

    start: function () {
        this.eventId = this.el.dataset.eventId;
    },

    _onTimezoneChange: async function (ev) {
        const result = await rpc(`/event/${this.eventId}/timezone_conversion`, {
            selected_tz: ev.target.value,
        });
        document.getElementById('converted_time_begin').value = result.converted_time_begin;
        document.getElementById('converted_date_begin').value = result.converted_date_begin;
        document.getElementById('converted_time_end').value = result.converted_time_end;
        document.getElementById('converted_date_end').value = result.converted_date_end;
    },

});

export default {
    EventTimezoneConverter: publicWidget.registry.EventTimezoneConverter,
};
