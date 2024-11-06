import { registry } from "@web/core/registry";

registry.category("services").add("website_page", {
    start() {
        const htmlEl = document.querySelector("html");
        const match = htmlEl.dataset.mainObject?.match(/(.+)\((\d+),(.*)\)/);
        return {
            mainObject: {
                model: match && match[1],
                id: match && (match[2] | 0),
            },
        };
    },
});
