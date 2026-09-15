import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("room_backend_tour", {
    url: "/odoo/meeting-rooms",
    steps: () => [
        {
            trigger: ".o_kanban_record:contains('Room 1')",
            content: "Open a room",
            run: "click",
        },
        {
            trigger: ".o_notebook .nav-link:contains('Room')",
            content: "Open the room's display settings",
            run: "click",
        },
        {
            trigger: "div[name='room_short_code'] input",
            content: "The room carries its kiosk short code",
            run: function () {
                if (this.anchor.value !== "room_1") {
                    throw new Error(`short code is ${this.anchor.value}`);
                }
            },
        },
        {
            trigger: ".o_menu_sections a:contains('Bookings')",
            content: "Go to the bookings",
            run: "click",
        },
        {
            trigger: ":is(.o_calendar_view, .o_gantt_view)",
            content: "Bookings open on the calendar, or the gantt when room_gantt is installed",
        },
        {
            trigger: ".o_switch_view.o_list",
            content: "Switch to the list",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: "Book a room",
            run: "click",
        },
        {
            trigger: "div[name='name'] input",
            content: "Name the meeting",
            run: "edit Tour meeting",
        },
        {
            trigger: "div[name='resource_ids'] input",
            content: "Pick a room",
            run: "edit Room 2",
        },
        {
            trigger: ".o-autocomplete--dropdown-item:contains('Room 2')",
            run: "click",
        },
        {
            trigger: ".o_form_button_save",
            content: "Save the booking",
            run: "click",
        },
        {
            trigger: ".o_form_saved",
        },
    ],
});
