import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { ScrollButtonOption } from "./scroll_button_option";
import { classAction } from "@html_builder/core/core_builder_action_plugin";

class ScrollButtonOptionPlugin extends Plugin {
    static id = "scrollButtonOption";
    resources = {
        builder_options: [
            {
                OptionComponent: ScrollButtonOption,
                selector: "section",
                exclude:
                    "[data-snippet] :not(.oe_structure) > [data-snippet],.s_instagram_page,.o_mega_menu > section,.s_appointments .s_dynamic_snippet_content",
            },
        ],
        builder_actions: {
            addScrollButton: {
                isApplied: ({ editingElement }) =>
                    !!editingElement.querySelector(":scope > .o_scroll_button"),
                apply: ({ editingElement }) => {
                    let button = this.buttonCache.get(editingElement);
                    if (!button) {
                        const anchor = document.createElement("a");
                        anchor.classList.add(
                            "o_scroll_button",
                            "mb-3",
                            "rounded-circle",
                            "align-items-center",
                            "justify-content-center",
                            "mx-auto",
                            "bg-primary",
                            "o_not_editable"
                        );
                        anchor.href = "#";
                        anchor.contentEditable = "false";
                        anchor.title = _t("Scroll down to next section");
                        const arrow = document.createElement("i");
                        arrow.classList.add("fa", "fa-angle-down", "fa-3x");
                        anchor.appendChild(arrow);
                        button = anchor;
                        this.buttonCache.set(editingElement, button);
                    }
                    editingElement.appendChild(button);
                },
                clean: this.removeButton.bind(this),
            },
            scrollButtonSectionHeightClassAction: {
                ...classAction,
                apply: (args) => {
                    classAction.apply(args);
                    const {
                        editingElement,
                        param: { mainParam },
                    } = args;
                    // If a "d-lg-block" class exists on the section (e.g., for
                    // mobile visibility option), it should be replaced with a
                    // "d-lg-flex" class. This ensures that the section has the
                    // "display: flex" property applied, which is the default
                    // rule for both "height" option classes.
                    if (mainParam) {
                        editingElement.classList.replace("d-lg-block", "d-lg-flex");
                    } else if (editingElement.classList.contains("d-lg-flex")) {
                        // There are no known cases, but we still make sure that
                        // the <section> element doesn't have a "display: flex"
                        // originally.
                        editingElement.classList.remove("d-lg-flex");
                        const sectionStyle = window.getComputedStyle(editingElement);
                        const hasDisplayFlex = sectionStyle.getPropertyValue("display") === "flex";
                        editingElement.classList.add(hasDisplayFlex ? "d-lg-flex" : "d-lg-block");
                    }
                },
                clean: (args) => {
                    classAction.clean(args);
                    if (args.param.mainParam === "o_full_screen_height") {
                        this.removeButton(args);
                    }
                },
            },
        },
    };

    setup() {
        this.buttonCache = new Map();
    }

    removeButton({ editingElement }) {
        const button = editingElement.querySelector(":scope > .o_scroll_button");
        if (button) {
            button.remove();
            this.buttonCache.set(editingElement, button);
        }
    }
}
registry.category("website-plugins").add(ScrollButtonOptionPlugin.id, ScrollButtonOptionPlugin);
