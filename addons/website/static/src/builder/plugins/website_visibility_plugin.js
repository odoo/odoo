import { Plugin } from "@html_editor/plugin";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { registry } from "@web/core/registry";

export class WebsiteVisibilityPlugin extends Plugin {
    static id = "websiteVisibilityPlugin";
    static dependencies = ["visibility", "history", "domObserver"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        system_classes: ["o_snippet_override_invisible", "o_conditional_hidden"],
        invisible_items: [
            {
                selector: ".o_snippet_mobile_invisible",
                isAvailable: () => this.config.isMobileView(this.editable),
                toggle: (el, show) => el.classList.toggle("o_snippet_override_invisible", show),
            },
            {
                selector: ".o_snippet_desktop_invisible",
                isAvailable: () => !this.config.isMobileView(this.editable),
                toggle: (el, show) => el.classList.toggle("o_snippet_override_invisible", show),
            },
            {
                selector: "[data-visibility=conditional]",
                toggle: (el, show) => el.classList.toggle("o_conditional_hidden", !show),
            },
        ],
        normalize_processors: (root) => {
            const allowedDeviceOverride = this.config.isMobileView(this.editable)
                ? ".o_snippet_mobile_invisible"
                : ".o_snippet_desktop_invisible";
            for (const el of selectElements(
                root,
                `.o_snippet_override_invisible:not(${allowedDeviceOverride})`
            )) {
                this.removeTemporaryClass(el, "o_snippet_override_invisible");
            }
            for (const el of selectElements(
                root,
                ".o_conditional_hidden:not([data-visibility=conditional])"
            )) {
                this.removeTemporaryClass(el, "o_conditional_hidden");
            }
            return root;
        },
        clean_for_save_processors: (root) => {
            for (const el of selectElements(root, ".o_snippet_override_invisible")) {
                el.classList.remove("o_snippet_override_invisible");
            }
            for (const el of selectElements(root, ".o_conditional_hidden")) {
                el.classList.remove("o_conditional_hidden");
            }
            return root;
        },
        on_mobile_view_switched_handlers: () => {
            const deviceSelector = ".o_snippet_desktop_invisible, .o_snippet_mobile_invisible";
            if (this.editable.querySelector(deviceSelector)) {
                for (const el of selectElements(
                    this.editable,
                    `:is(${deviceSelector}).o_snippet_override_invisible`
                )) {
                    el.classList.remove("o_snippet_override_invisible");
                }
                this.dependencies.visibility.invalidateVisibility();
            }
        },
        snippet_preview_dialog_iframe_processors: (params) => {
            params.iframe.contentDocument.body.classList.add("o_conditional_visibility_ready");
            return params;
        },
    };

    setup() {
        const styleSheet = this.document.querySelector("style#conditional_visibility");
        if (styleSheet) {
            styleSheet.disabled = true;
        }
    }

    removeTemporaryClass(el, className) {
        if (el.classList.contains(className)) {
            if (this.dependencies.history.getIsPreviewing()) {
                this.dependencies.domObserver.applyCustomMutation({
                    apply: () => el.classList.remove(className),
                    revert: () => el.classList.add(className),
                });
            } else {
                el.classList.remove(className);
            }
        }
    }
}

registry.category("website-plugins").add(WebsiteVisibilityPlugin.id, WebsiteVisibilityPlugin);
registry.category("translation-plugins").add(WebsiteVisibilityPlugin.id, WebsiteVisibilityPlugin);
