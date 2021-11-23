odoo.define("calendar_ical.CalendarSubscribe", function (require) {
    "use strict";

    const AbstractAction = require("web.AbstractAction");
    const core = require("web.core");

    const CalendarSubscribe = AbstractAction.extend({
        template: "calendar_ical.CalendarSubscribe",

        /**
         * @override
         */
        init: function (parent, action) {
            action.name = "Subscribe to Calendar"
            this._super(...arguments);
            this.calendar_url = action.context.calendar_url;
        },
    });

    core.action_registry.add("calendar_subscribe", CalendarSubscribe);

    return CalendarSubscribe;
});
