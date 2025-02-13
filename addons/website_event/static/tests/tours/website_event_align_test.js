import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_event_submenu_align_breadcrumb_tour", {
    url: "/event",
    steps: () => [{
        content: 'Go on "Test Event" page',
        trigger: 'a[href*="/event"]:contains("Test Event"):first',
        run: "click",
    }, {
        trigger: 'body:has(.o_wevent_event)',
        content: 'Wait for the page to load',
    },  {
        content: 'Open editor',
        trigger: '.o_frontend_to_backend_edit_btn',
        run: 'click'
    }, {
        trigger: '.o-website-btn-custo-primary:contains("Edit")',
        content: "Click here to enter edit mode for the event page.",
        run: "click",
    },{
        trigger: 'button.o_we_customize_snippet_btn',
        content: "This is the main container for your event page options.",
        run: "click",
    }, {
        trigger: 'we-button-group[data-dependencies="is_submenu"] .fa-align-left',
        content: "Click here to align the sub-menu to the left.",
        run: "click",
    }, {
        trigger: 'we-button-group[data-dependencies="is_submenu"] .fa-align-left.active',
        content: 'Wait for the page to load',
    }, {
        trigger: 'we-button-group[data-dependencies="is_submenu"] .fa-align-center',
        content: "Click here to center-align the sub-menu.",
        run: "click",
    }, {
        trigger: 'we-button-group[data-dependencies="is_submenu"] .fa-align-center.active',
        content: 'Wait for the page to load',
    }, {
        trigger: 'we-button-group[data-dependencies="is_submenu"] .fa-align-right',
        content: "Click here to align the sub-menu to the right.",
        run: "click",
    }, {
        trigger: 'we-button-group[data-dependencies="is_submenu"] .fa-align-right.active',
        content: 'Wait for the page to load',
    }, {
        trigger: 'we-button[data-customize-website-views="website_event.breadcrumb_template"] we-checkbox',
        content: "Toggle this checkbox to show or hide breadcrumbs on the event page.",
        run: "click",
    }, {
        trigger: 'we-button[data-customize-website-views="website_event.breadcrumb_template"]:not(.active)',
        content: 'Wait for the breadcrumbs to be turned off',
    }, {
        trigger: "button[data-action=save]",
        content: "Once you click on save, your event page is updated.",
        run: "click",
    }]
});
