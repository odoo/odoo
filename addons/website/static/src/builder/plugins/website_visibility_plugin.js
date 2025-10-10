import { Plugin } from "@html_editor/plugin";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { registry } from "@web/core/registry";

export class WebsiteVisibilityPlugin extends Plugin {
    static id = "websiteVisibilityPlugin";
    static dependencies = ["visibility"];

    resources = {
        system_classes: ["o_snippet_override_invisible", "o_conditional_hidden"],
        invisible_items: [
            {
                selector: ".o_snippet_mobile_invisible",
                isDisabled: () => !this.config.isMobileView(this.editable),
                toggle: (el, show) => el.classList.toggle("o_snippet_override_invisible", show),
            },
            {
                selector: ".o_snippet_desktop_invisible",
                isDisabled: () => this.config.isMobileView(this.editable),
                toggle: (el, show) => el.classList.toggle("o_snippet_override_invisible", show),
            },
            {
                selector: "[data-visibility=conditional]",
                toggle: (el, show) => el.classList.toggle("o_conditional_hidden", !show),
            },
            {
                selector: "#wrapwrap > :is(header, footer).d-none",
                toggle: (el, show) => el.classList.toggle("o_snippet_override_invisible", show),
            },
        ],
        /** @param {import("@html_editor/core/history_plugin").HistoryMutationRecord[]} records */
        handleNewRecords: (records) => {
            for (const record of records) {
                const { type, className, attributeName, oldValue, value, target } = record;
                if (
                    type === "classList" &&
                    (className === "o_snippet_mobile_invisible" ||
                        className === "o_snippet_desktop_invisible") &&
                    oldValue === true &&
                    value === false
                ) {
                    target.classList.remove("o_snippet_override_invisible");
                }
                if (
                    type === "attributes" &&
                    attributeName === "data-visibility" &&
                    oldValue === "conditional" &&
                    value !== "conditional"
                ) {
                    target.classList.remove("o_conditional_hidden");
                }
                if (
                    type === "classList" &&
                    className === "d-none" &&
                    oldValue === true &&
                    value === false &&
                    target.matches("#wrapwrap > :is(header, footer)")
                ) {
                    target.classList.remove("o_snippet_override_invisible");
                }
            }
        },
        clean_for_save_handlers: ({ root }) => {
            for (const el of selectElements(root, ".o_snippet_override_invisible")) {
                el.classList.remove("o_snippet_override_invisible");
            }
            for (const el of selectElements(root, "[data-visibility=conditional]")) {
                el.classList.add("o_conditional_hidden");
            }
        },
        device_view_switched_handlers: () => {
            const deviceSelector = ".o_snippet_desktop_invisible, .o_snippet_mobile_invisible";
            if (this.editable.querySelector(deviceSelector)) {
                for (const el of selectElements(
                    this.editable,
                    `${deviceSelector}.o_snippet_override_invisible`
                )) {
                    el.classList.remove("o_snippet_override_invisible");
                }
                this.dependencies.visibility.invalidateVisibility();
            }
        },
    };
}

registry.category("website-plugins").add(WebsiteVisibilityPlugin.id, WebsiteVisibilityPlugin);
