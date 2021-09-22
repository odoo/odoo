odoo.define('event.event_steps', function (require) {
"use strict";

var core = require('web.core');

var EventAdditionalTourSteps = core.Class.extend({

    _get_website_event_steps: function () {
        return [false];
    },

});

return EventAdditionalTourSteps;

});

odoo.define('event.event_tour', function (require) {
"use strict";

const {_t} = require('web.core');
const {Markup} = require('web.utils');

var tour = require('web_tour.tour');
var EventAdditionalTourSteps = require('event.event_steps');

tour.register('event_tour', {
    url: '/web',
    rainbowManMessage: _t("Great! Now all you have to do is wait for your attendees to show up!"),
    sequence: 210,
}, [tour.stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="event.event_main_menu"]',
    content: Markup(_t("Ready to <b>organize events</b> in a few minutes? Let's get started!")),
    position: 'bottom',
    edition: 'enterprise',
}, {
    trigger: '.o_app[data-menu-xmlid="event.event_main_menu"]',
    content: Markup(_t("Ready to <b>organize events</b> in a few minutes? Let's get started!")),
    edition: 'community',
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_event_kanban_view',
    content: Markup(_t("Let's create your first <b>event</b>.")),
    position: 'bottom',
    width: 175,
}, {
    trigger: '.o_event_form_view input[name="name"]',
    content: Markup(_t("This is the <b>name</b> your guests will see when registering.")),
    run: 'text Odoo Experience 2020',
}, {
    trigger: '.o_event_form_view input[name="date_end"]',
    content: Markup(_t("When will your event take place? <b>Select</b> the start and end dates <b>and click Apply</b>.")),
    run: function () {
        $('input[name="date_begin"]').val('09/30/2020 08:00:00').change();
        $('input[name="date_end"]').val('10/02/2020 23:00:00').change();
    },
}, {
    trigger: '.o_event_form_view div[name="event_ticket_ids"] .o_field_x2many_list_row_add a',
    content: Markup(_t("Ticket types allow you to distinguish your attendees. Let's <b>create</b> a new one.")),
}, ...new EventAdditionalTourSteps()._get_website_event_steps(), {
    trigger: '.o_event_form_view div[name="stage_id"]',
    extra_trigger: 'div.o_form_buttons_view:not(.o_hidden)',
    content: _t("Now that your event is ready, click here to move it to another stage."),
    position: 'bottom',
}, {
    trigger: 'ol.breadcrumb li.breadcrumb-item:first',
    extra_trigger: '.o_event_form_view div[name="stage_id"]',
    content: Markup(_t("Use the <b>breadcrumbs</b> to go back to your kanban overview.")),
    position: 'bottom',
    run: 'click',
}].filter(Boolean));

});
