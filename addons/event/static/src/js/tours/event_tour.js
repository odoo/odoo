import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

import EventAdditionalTourSteps from "@event/js/tours/event_steps";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('event_tour', {
    steps: () => [stepUtils.showAppsMenuItem(), {
    isActive: ["enterprise"],
    trigger: '.o_app[data-menu-xmlid="event.event_main_menu"]',
    content: markup(_t("Ready to <b>organize events</b> in a few minutes? Let's get started!")),
    run: "click",
}, {
    isActive: ["community"],
    trigger: '.o_app[data-menu-xmlid="event.event_main_menu"]',
    content: markup(_t("Ready to <b>organize events</b> in a few minutes? Let's get started!")),
    run: "click",
},
{
    trigger: ".o_event_kanban_view",
},
{
    trigger: '.o-kanban-button-new',
    content: markup(_t("Let's create your first <b>event</b>.")),
    run: "click",
}, {
    trigger: '.o_event_form_view div[name="name"] textarea',
    content: markup(_t("This is the <b>name</b> your guests will see when registering.")),
    run: "edit Odoo Experience 2020",
}, {
    trigger: '.o_event_form_view div[name="date_begin"] .o_input',
    content: markup(_t("Open date range picker.<br/>Pick a Start and End date for your event.")),
    run: "click",
}, {
    content: _t("Pick a start date."),
    trigger: ".o_datetime_picker .o_date_item_cell.o_today",
    run: "click",
}, {
    content: _t("Pick an end date."),
    trigger: ".o_datetime_picker .o_date_item_cell.o_today ~ .o_date_item_cell:eq(1)",
    run: "click",
}, {
    content: _t("Confirm the selected dates."),
    trigger: ".o_datetime_buttons button.btn-primary",
    run: "click",
}, {
    content: _t("Open the Tickets tab."),
    trigger: '.o_event_form_view .o_notebook .nav-link:contains("Tickets")',
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: '.o_event_form_view div[name="event_ticket_ids"] .o_field_x2many_list_row_add button',
    content: markup(_t("Ticket types allow you to distinguish your attendees. Let's <b>create</b> a new one.")),
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: '.o_event_form_view div[name="event_ticket_ids"] .o-kanban-button-new',
    content: _t("Ticket types allow you to distinguish your attendees. Let's create a new one."),
    run: "click",
}, {
    isActive: ["mobile"],
    content: _t("Save the ticket."),
    trigger: '.o_dialog .o_form_button_save',
    run: "click",
}, stepUtils.autoExpandMoreButtons(),
...new EventAdditionalTourSteps()._get_website_event_steps(), {
    trigger: '.o_event_form_view div[name="stage_id"]',
    content: _t("Now that your event is ready, click here to move it to another stage."),
    run: "click",
},
{
    trigger: `.o_event_form_view div[name="stage_id"]`,
},
{
    isActive: ["desktop"],
    trigger: '.o_menu_sections a[data-menu-xmlid="event.menu_event_event"]',
    content: _t("Use the breadcrumbs to go back to your kanban overview."),
    run: 'click',
}, {
    isActive: ["mobile"],
    trigger: '.o_menu_toggle',
    content: _t("Use the breadcrumbs to go back to your kanban overview."),
    run: 'click',
}, {
    isActive: ["mobile"],
    trigger: '.o_burger_menu_content [data-menu-xmlid="event.menu_event_event"]',
    run: 'click',
}, {
    trigger: ".o_event_kanban_view",
}].filter(Boolean)});
