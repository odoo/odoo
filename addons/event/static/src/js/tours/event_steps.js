/** @odoo-module alias=event.event_steps **/

import core from "web.core";

var EventAdditionalTourSteps = core.Class.extend({

    _get_website_event_steps: function () {
        return [false];
    },

});

export default EventAdditionalTourSteps;
