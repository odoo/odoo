import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";

class CookiesBarOptionPlugin extends Plugin {
    static id = "CookiesBarOptionPlugin";
    resources = {
        builder_options: [
            {
                template: "website.CookiesBarOption",
                selector: "#website_cookies_bar",
                applyTo: ".modal",
            },
        ],
        builder_actions: this.getActions(),
    };

    getDialogEl(editingElement) {
        return editingElement.querySelector(".modal-dialog");
    }

    getActions() {
        return {
            selectLayout: {
                apply: ({ editingElement, value: layout }) => {
                    const templateEl = renderToElement(`website.cookies_bar.${layout}`, {
                        websiteId: this.services.website.currentWebsite.id,
                    });
                    const contentEl = editingElement.querySelector(".modal-content");

                    // The selectors' order is significant since some selectors
                    // may be nested within others, and we want to preserve the
                    // nested ones.
                    // For instance, in the case of '.o_cookies_bar_text_policy'
                    // nested inside '.o_cookies_bar_text_secondary', the parent
                    // selector should be copied first, followed by the child
                    // selector to ensure that the content of the nested
                    // selector is not overwritten.
                    const selectorsToKeep = [
                        ".o_cookies_bar_text_button",
                        ".o_cookies_bar_text_button_essential",
                        ".o_cookies_bar_text_title",
                        ".o_cookies_bar_text_primary",
                        ".o_cookies_bar_text_secondary",
                        ".o_cookies_bar_text_policy",
                    ];

                    if (this.savedSelectors === undefined) {
                        this.savedSelectors = [];
                    }

                    for (const selector of selectorsToKeep) {
                        const currentLayoutEls = contentEl.querySelectorAll(`${selector} > *`);
                        const newLayoutEl = templateEl.querySelector(selector);
                        if (currentLayoutEls.length) {
                            // Save value before change, eg 'title' is not
                            // inside the 'discrete' template but we want to
                            // preserve it in case we select another layout
                            // later
                            this.savedSelectors[selector] = currentLayoutEls;
                        }
                        const savedSelector = this.savedSelectors[selector];
                        if (newLayoutEl && savedSelector?.length) {
                            newLayoutEl.replaceChildren(savedSelector);
                        }
                    }

                    contentEl.replaceChildren(templateEl);

                    switch (layout) {
                        case "discrete":
                        case "classic":
                            editingElement.classList.add("s_popup_bottom");
                            this.getDialogEl(editingElement).classList.add("s_popup_size_full");
                            break;
                        case "popup":
                            editingElement.classList.add("s_popup_middle");
                            break;
                    }
                },
                clean: ({ editingElement }) => {
                    // See popup_option.xml > Position option
                    const positionClasses = ["s_popup_top", "s_popup_middle", "s_popup_bottom"];
                    // See popup_option.xml > Size option
                    const sizeClasses = ["modal-sm", "modal-lg", "modal-xl", "s_popup_size_full"];
                    editingElement.classList.remove(...positionClasses);
                    this.getDialogEl(editingElement).classList.remove(...sizeClasses);
                },
            },
        };
    }
}

registry.category("website-plugins").add(CookiesBarOptionPlugin.id, CookiesBarOptionPlugin);
