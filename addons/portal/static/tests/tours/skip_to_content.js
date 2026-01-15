import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("skip_to_content", {
    url: "/",
    steps: () => [
        {
            content: "Make sure that Skip to Content button is on top of all the links present in header",
            trigger: "a:first-child[class~='o_skip_to_content']",
            run: "click"
        },
        {
            content: "Check if we have been redirected to #wrap",
            trigger: "body",
            run: () => {
                if (!window.location.href.endsWith("#wrap")) {
                    console.error("We should be on #wrap.");
                }
            }
        }
    ]
});
