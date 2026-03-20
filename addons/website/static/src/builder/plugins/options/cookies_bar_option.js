import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";

/**
 * @typedef { Object } CookiesBarOptionShared
 * @property { CookiesBarOptionPlugin['getSavedSelectors'] } getSavedSelectors
 */

export class CookiesBarOption extends BaseOptionComponent {
    static template = "website.CookiesBarOption";
    static selector = "#website_cookies_bar";
    static applyTo = ".modal";
}
class CookiesBarOptionPlugin extends Plugin {
    static id = "CookiesBarOptionPlugin";
    static shared = ["getSavedSelectors"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [CookiesBarOption],
        builder_actions: {
            SelectLayoutAction,
        },
    };

    setup() {
        this.savedSelectors = {};
    }

    getSavedSelectors() {
        return this.savedSelectors;
    }
}

export class SelectLayoutAction extends BuilderAction {
    static id = "selectLayout";
    static dependencies = ["CookiesBarOptionPlugin"];
    apply({ editingElement, value: layout }) {
        const savedSelectors = this.dependencies.CookiesBarOptionPlugin.getSavedSelectors();
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

        for (const selector of selectorsToKeep) {
            const currentLayoutEls = contentEl.querySelector(selector)?.childNodes;
            const newLayoutEl = templateEl.querySelector(selector);
            if (currentLayoutEls && currentLayoutEls.length) {
                // Save value before change, eg 'title' is not
                // inside the 'discrete' template but we want to
                // preserve it in case we select another layout
                // later
                savedSelectors[selector] = [...currentLayoutEls];
            }
            const savedSelector = savedSelectors[selector];
            if (newLayoutEl && savedSelector?.length) {
                newLayoutEl.replaceChildren(...savedSelector);
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
    }
    clean({ editingElement }) {
        // See popup_option.xml > Position option
        const positionClasses = ["s_popup_top", "s_popup_middle", "s_popup_bottom"];
        // See popup_option.xml > Size option
        const sizeClasses = ["modal-sm", "modal-lg", "modal-xl", "s_popup_size_full"];
        editingElement.classList.remove(...positionClasses);
        this.getDialogEl(editingElement).classList.remove(...sizeClasses);
    }
    getDialogEl(editingElement) {
        return editingElement.querySelector(".modal-dialog");
    }
}

registry.category("website-plugins").add(CookiesBarOptionPlugin.id, CookiesBarOptionPlugin);
