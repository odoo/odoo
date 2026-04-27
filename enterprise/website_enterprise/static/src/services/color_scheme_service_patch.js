import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";
import { colorSchemeService } from "@web_enterprise/webclient/color_scheme/color_scheme_service";

patch(colorSchemeService, {
    reload() {
        if (document.querySelector("header.o_navbar + .o_action_manager > .o_website_preview")) {
            browser.location.pathname = "/@" + browser.location.pathname;
        } else {
            super.reload();
        }
    },
});
