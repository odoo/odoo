import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { uniqueId } from "@web/core/utils/functions";
import { getElementsWithOption } from "@html_builder/utils/utils";
import { NavTabsHeaderMiddleButtons } from "./navtabs_header_buttons";

const tabsSectionSelector = "section.s_tabs, section.s_tabs_images";

class NavTabsOptionPlugin extends Plugin {
    static id = "navTabsOption";
    static dependencies = ["clone"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_header_middle_buttons: {
            Component: NavTabsHeaderMiddleButtons,
            selector: tabsSectionSelector,
            props: {
                addItem: async (editingElement) => await this.addItem(editingElement),
                removeItem: (editingElement) => this.removeItem(editingElement),
            },
        },
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        on_cloned_handlers: this.onCloned.bind(this),
    };

    getNavLinkEls(editingElement) {
        const navEl = editingElement.querySelector(".nav");
        return navEl.querySelectorAll(".nav-item .nav-link");
    }
    getPaneEls(editingElement) {
        const tabContentEl = editingElement.querySelector(".tab-content");
        return tabContentEl.querySelectorAll(":scope > .tab-pane");
    }
    getActiveLinkEl(editingElement) {
        const navEl = editingElement.querySelector(".nav");
        return navEl.querySelector(".nav-link.active");
    }
    getActivePaneEl(editingElement) {
        const tabContentEl = editingElement.querySelector(".tab-content");
        return tabContentEl.querySelector(":scope > .tab-pane.active");
    }

    showTab(navLinkEl, paneEl) {
        this.window.Tab.getOrCreateInstance(navLinkEl).show();
        // Immediately show the pane so the history remains consistent.
        paneEl.classList.add("show");
    }

    async addItem(editingElement) {
        const activeNavItemEl = this.getActiveLinkEl(editingElement).parentElement;
        const activePaneEl = this.getActivePaneEl(editingElement);

        const newPaneEl = await this.dependencies.clone.cloneElement(activePaneEl);
        const newNavItemEl = activeNavItemEl.cloneNode(true);
        activeNavItemEl.after(newNavItemEl);
        // To make sure the DOM is clean and correct, leave it to Bootstrap to
        // update it. We leave `.active` only on the former active elements.
        newPaneEl.classList.remove("active", "show");
        newNavItemEl.firstElementChild.classList.remove("active");
        this.generateUniqueIDs(editingElement);
        this.showTab(newNavItemEl.querySelector(".nav-link"), newPaneEl);
    }

    removeItem(editingElement) {
        const activeLinkEl = this.getActiveLinkEl(editingElement);
        const activePaneEl = this.getActivePaneEl(editingElement);
        // Show the next tab.
        const navLinkEls = [...this.getNavLinkEls(editingElement)];
        const index = (navLinkEls.indexOf(activeLinkEl) + 1) % navLinkEls.length;
        const nextActiveLinkEl = navLinkEls[index];
        const nextActivePaneEl = [...this.getPaneEls(editingElement)][index];
        this.showTab(nextActiveLinkEl, nextActivePaneEl);
        // Remove the tab.
        activeLinkEl.parentElement.remove();
        activePaneEl.remove();
    }

    onSnippetDropped({ snippetEl }) {
        const tabsEls = getElementsWithOption(snippetEl, tabsSectionSelector);
        for (const tabsEl of tabsEls) {
            this.generateUniqueIDs(tabsEl);
        }
    }

    onCloned({ cloneEl }) {
        const tabsEls = getElementsWithOption(cloneEl, tabsSectionSelector);
        for (const tabsEl of tabsEls) {
            this.generateUniqueIDs(tabsEl);
        }
    }

    generateUniqueIDs(editingElement) {
        const navLinkEls = this.getNavLinkEls(editingElement);
        const tabPaneEls = this.getPaneEls(editingElement);
        for (let i = 0; i < navLinkEls.length; i++) {
            const id = uniqueId(new Date().getTime() + "_");
            const idLink = "nav_tabs_link_" + id;
            const idContent = "nav_tabs_content_" + id;
            const navLinkEl = navLinkEls[i];
            navLinkEl.id = idLink;
            navLinkEl.href = "#" + idContent;
            navLinkEl.setAttribute("aria-controls", idContent);
            const tabPaneEl = tabPaneEls[i];
            tabPaneEl.id = idContent;
            tabPaneEl.setAttribute("aria-labelledby", idLink);
        }
    }
}
registry.category("website-plugins").add(NavTabsOptionPlugin.id, NavTabsOptionPlugin);
