import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("discuss_announcement_channel_tour", {
    url: "/odoo",
    steps: () => [
        {
            isActive: ["enterprise"],
            trigger: "a[data-menu-xmlid='mail.menu_root_discuss']",
            run: "click",
        },
        {
            trigger: ".o-mail-DiscussSearch-inputContainer",
            run: "click",
        },
        {
            trigger: ".o_command_palette_search input",
            run: `edit AnnouncementChannel_${new Date().getTime()}`,
        },
        {
            trigger: ".o-mail-DiscussCommand-createAnnouncementChannel",
            run: "click",
        },
        {
            trigger: ".o-mail-Composer-input",
            run: `edit Welcome to the Announcement channel!_${new Date().getTime()}`,
        },
        {
            trigger: ".o-mail-Composer-input",
            run: "press Enter",
        },
        {
            trigger: ".o-mail-DiscussSearch-inputContainer",
            run: "click",
        },
        {
            trigger: ".o_command_palette_search input",
            run: `edit Channel_${new Date().getTime()}`,
        },
        {
            trigger: ".o-mail-DiscussCommand-createChannel",
            run: "click",
        },
        {
            trigger: ".o-mail-ActionList-button[title='Announcements']",
            run: "click",
        },
        {
            trigger: ".o-mail-DiscussSidebarSubchannel:contains('Announcements')",
            run: "click",
        },
        {
            trigger: ".o-mail-Composer-input",
            run: "edit Welcome to the Announcement sub-channel",
        },
        {
            trigger: ".o-mail-Composer-input",
            run: "press Enter",
        },
        {
            trigger: "button[title='View or join announcements']:not(:visible)",
            run: "click",
        },
        {
            trigger: ".o-kanban-button-new",
            run: "click",
        },
        {
            trigger: "#name_0",
            run: `edit NewAnnouncementChannel_${new Date().getTime()}`,
        },
        {
            trigger: "button.o_form_button_save",
            run: "click",
        },
        {
            trigger: ".nav .nav-item a:contains('Members')",
            run: "click",
        },
        {
            trigger: "[name='partner_id']:contains('Admin')",
        },
        {
            trigger: "[name='member_type']:contains('Admin')",
        },
        {
            trigger: ".o_field_x2many_list_row_add a:contains('Add a line')",
            run: "click",
        },
        {
            trigger: "[name='partner_id'] input",
            run: "edit Demo",
        },
        {
            trigger: "#autocomplete_0_0:contains('Demo')",
            run: "click",
        },
        {
            trigger: "tr[data-id='datapoint_20'] td[name='member_type'] input",
            run: "click",
        },
        {
            trigger: ".o-dropdown-item:contains('Admin')",
            run: "click",
        },
        {
            trigger: "button.o_form_button_save",
            run: "click",
        },
        {
            trigger: "button[data-menu-xmlid='mail.menu_channel']",
            run: "click",
        },
        {
            trigger: "a[data-menu-xmlid='mail.menu_announcements']",
            run: "click",
        },
        {
            trigger: ".o_kanban_record:contains('NewAnnouncementChannel')",
        },
    ],
});
