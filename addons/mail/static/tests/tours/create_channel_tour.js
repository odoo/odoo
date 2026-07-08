import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("can_create_channel_from_form_view", {
    steps: () => [
        {
            trigger: ".o-mail-NotificationItem:has(:text('OdooBot'))",
            run: "click",
        },
        {
            trigger: ".o-mail-DiscussContent-threadName[title='OdooBot']",
        },
        { trigger: ".o-mail-MessagingMenu-tab:has(:text('Channels'))", run: "click" },
        { trigger: "button[title='New channel']", run: "click" },
        {
            trigger: ".o_control_panel_main_buttons button:contains('New')",
            run: "click",
        },
        {
            trigger: "div[name='name'] input",
            run: "edit Test channel",
        },
        {
            trigger: ".breadcrumb .dropdown-toggle",
            content: "Open the breadcrumb dropdown",
            run: "click",
        },
        {
            trigger: '.o-overlay-container .dropdown-menu a:contains("OdooBot")',
            run: "click",
        },
        { trigger: ".o-mail-MessagingMenu-tab:has(:text('Channels'))", run: "click" },
        {
            trigger: ".o-mail-MessagingMenuItem:has(:text('Test channel'))",
        },
        // clicking on the channel should open the chat window
        { trigger: "button[title='New channel']", run: "click" },
        { trigger: "span:text('Sports')", run: "click" },
        { trigger: ".o-mail-ChatWindow" },
    ],
});
