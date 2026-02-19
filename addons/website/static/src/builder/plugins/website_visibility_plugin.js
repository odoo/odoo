import { Plugin } from "@html_editor/plugin";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { registry } from "@web/core/registry";

export class WebsiteVisibilityPlugin extends Plugin {
    static id = "websiteVisibilityPlugin";
    static dependencies = ["visibility", "history"];

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
            {
                selector: ":is(#wrapwrap > :is(header, footer), .o_page_breadcrumb).d-none",
                toggle: (el, show) => el.classList.toggle("o_snippet_override_invisible", show),
            },
        ],
        on_snippet_dropped_handlers: ({ snippetEl }) => {
            for (const el of selectElements(snippetEl, "[data-visibility=conditional]")) {
                el.classList.remove("o_conditional_hidden");
            }
        },
        normalize_handlers: (root) => {
            const allowedDeviceOverride = this.config.isMobileView(this.editable)
                ? ".o_snippet_mobile_invisible"
                : ".o_snippet_desktop_invisible";
            for (const el of selectElements(
                root,
                `.o_snippet_override_invisible:not(${allowedDeviceOverride}, :is(#wrapwrap > :is(header, footer), .o_page_breadcrumb).d-none)`
            )) {
                this.removeTemporaryClass(el, "o_snippet_override_invisible");
            }
            for (const el of selectElements(
                root,
                ".o_conditional_hidden:not([data-visibility=conditional])"
            )) {
                this.removeTemporaryClass(el, "o_conditional_hidden");
            }
        },
        clean_for_save_handlers: ({ root }) => {
            for (const el of selectElements(root, ".o_snippet_override_invisible")) {
                el.classList.remove("o_snippet_override_invisible");
            }
            for (const el of selectElements(root, "[data-visibility=conditional]")) {
                // we add `o_conditional_hidden` in the saved version,
                // and it will be removed on load in `unhideConditionalElements`
                el.classList.add("o_conditional_hidden");
            }
        },
        device_view_switched_handlers: () => {
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
        editor_enabled_handlers: () => this.dependencies.visibility.invalidateVisibility(),
    };

    removeTemporaryClass(el, className) {
        if (el.classList.contains(className)) {
            if (this.dependencies.history.getIsPreviewing()) {
                this.dependencies.history.applyCustomMutation({
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
