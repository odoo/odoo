import { isMobileView } from "@html_builder/utils/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import {
    DEVICE_VISIBILITY_OPTION_SELECTOR,
    VISIBILITY_OPTION_SELECTOR,
} from "./options/visibility_option_plugin";

export class WebsiteVisibilityPlugin extends Plugin {
    static id = "websiteVisibilityPlugin";

    resources = {
        system_classes: ["o_conditional_hidden"],
        target_show: this.onTargetShow.bind(this),
        target_hide: this.onTargetHide.bind(this),
    };

    onTargetHide(editingEl) {
        if (
            editingEl.matches(DEVICE_VISIBILITY_OPTION_SELECTOR) ||
            editingEl.matches(VISIBILITY_OPTION_SELECTOR)
        ) {
            editingEl.classList.remove("o_snippet_override_invisible");

            const isConditionalHidden = editingEl.matches("[data-visibility='conditional']");
            if (isConditionalHidden) {
                editingEl.classList.add("o_conditional_hidden");
            }
        }
    }

    onTargetShow(editingEl) {
        if (
            editingEl.matches(DEVICE_VISIBILITY_OPTION_SELECTOR) ||
            editingEl.matches(VISIBILITY_OPTION_SELECTOR)
        ) {
            const isMobilePreview = isMobileView(editingEl);
            const isMobileHidden = editingEl.classList.contains("o_snippet_mobile_invisible");
            const isDesktopHidden = editingEl.classList.contains("o_snippet_desktop_invisible");
            if ((isMobileHidden && isMobilePreview) || (isDesktopHidden && !isMobilePreview)) {
                editingEl.classList.add("o_snippet_override_invisible");
            }

            editingEl.classList.remove("o_conditional_hidden");
        }
    }
}

registry.category("website-plugins").add(WebsiteVisibilityPlugin.id, WebsiteVisibilityPlugin);
