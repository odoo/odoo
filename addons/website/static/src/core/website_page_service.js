import { jsToPyLocale } from "@web/core/l10n/utils";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { unslugHtmlDataObject } from "@website/utils/misc";

export const websitePageService = {
    start() {
        const htmlEl = document.querySelector("html");

        return {
            context: {
                ...user.context,
                website_id: htmlEl.dataset.websiteId | 0,
                lang: jsToPyLocale(htmlEl.getAttribute("lang")) || "en_US",
                user_lang: user.context.lang,
            },
            mainObject: unslugHtmlDataObject(htmlEl.dataset.mainObject) || {},
        };
    },
};

registry.category("services").add("website_page", websitePageService);
