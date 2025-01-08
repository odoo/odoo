import { jsToPyLocale } from "@web/core/l10n/utils";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

registry.category("services").add("website_page", {
    start() {
        const htmlEl = document.querySelector("html");
        const match = htmlEl.dataset.mainObject?.match(/(.+)\((\d+),(.*)\)/);

        return {
            context: {
                ...user.context,
                website_id: htmlEl.dataset.websiteId | 0,
                lang: jsToPyLocale(htmlEl.getAttribute("lang")) || "en_US",
                user_lang: user.context.lang,
            },
            mainObject: {
                model: match && match[1],
                id: match && (match[2] | 0),
            },
        };
    },
});
