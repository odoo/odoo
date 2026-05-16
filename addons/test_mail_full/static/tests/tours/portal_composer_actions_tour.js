import { registry } from "@web/core/registry";

const cannedResponseButtonSelector = "button[title='Insert a Canned response']";

registry.category("web_tour.tours").add("portal_composer_actions_tour_internal_user", {
    steps: () => [
        {
            trigger: `#chatterRoot:shadow .o-mail-Composer ${cannedResponseButtonSelector}`,
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Composer-input",
            run() {
                if (this.anchor.value !== "::") {
                    console.error(
                        "Clicking on the canned response button should insert the '::' into the composer."
                    );
                }
            },
        },
        {
            trigger:
                "#chatterRoot:shadow .o-mail-Composer-suggestion:contains(Hello, how may I help you?)",
        },
    ],
});

registry.category("web_tour.tours").add("portal_composer_actions_tour_portal_user", {
    steps: () => [
        {
            trigger: `#chatterRoot:shadow .o-mail-Composer:not(:has(${cannedResponseButtonSelector}))`,
        },
    ],
});
