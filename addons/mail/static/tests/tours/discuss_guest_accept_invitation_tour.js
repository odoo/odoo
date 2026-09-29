import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("discuss.guest_accept_invitation", {
    steps: () => [
        {
            trigger: ".o-mail-WelcomePage input:value('alfred@test.com')",
            run: "edit Alfredo Pasta",
        },
        {
            trigger: "button:contains(Join Conversation)",
            run: "click",
        },
        {
            trigger: ".o-mail-Discuss",
        },
    ],
});
