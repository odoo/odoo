import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_unsplash_beacon", {
    steps: () => [
        {
            content: "Verify whether beacon was sent.",
            trigger: 'img[data-beacon="sent"]',
        },
    ],
});
