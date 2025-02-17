import { useDomState } from "@html_builder/core/building_blocks/utils";
import { useOperation } from "@html_builder/core/plugins/operation_plugin";
import { Plugin } from "@html_editor/plugin";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { uniqueId } from "@web/core/utils/functions";

class NavTabsPlugin extends Plugin {
    static id = "NavTabsOption";
    static dependencies = ["clone", "remove"];
    resources = {
        builder_header_middle_buttons: {
            Component: NavTabsHeaderMiddleButtons,
            selector: "section.s_tabs",
            props: {
                addItem: (editingElement) => this.addItem(editingElement),
                removeItem: (editingElement) => this.removeItem(editingElement),
            },
        },
        normalize_handlers: this.onNormalize.bind(this),
    };

    getNavLinkEls(editingElement) {
        return editingElement.querySelectorAll(".nav-item .nav-link");
    }
    getPaneEls(editingElement) {
        return editingElement.querySelectorAll(".tab-content > .tab-pane");
    }
    getActiveLinkEl(editingElement) {
        return editingElement.querySelector(".nav-link.active");
    }
    getActivePaneEl(editingElement) {
        return editingElement.querySelector(".tab-pane.active");
    }

    showTab(navLinkEl, paneEl) {
        this.document.defaultView.Tab.getOrCreateInstance(navLinkEl).show();
        // Immediately show the pane so the history remains consistent.
        paneEl.classList.add("show");
    }

    addItem(editingElement) {
        const activeLinkEl = this.getActiveLinkEl(editingElement);
        const activePaneEl = this.getActivePaneEl(editingElement);

        const activeNavItemEl = activeLinkEl.parentElement;
        const newNavItemEl = this.dependencies.clone.cloneElement(activeNavItemEl);
        const newPaneEl = this.dependencies.clone.cloneElement(activePaneEl);
        // To make sure the DOM is clean and correct, leave it to Bootstrap to
        // update it. We leave `.active` only on the former active elements.
        newNavItemEl.firstElementChild.classList.remove("active");
        newPaneEl.classList.remove("active", "show");
        this.generateUniqueIDs(editingElement);
        this.showTab(newNavItemEl.querySelector(".nav-link"), newPaneEl);
    }

    removeItem(editingElement) {
        const activeLinkEl = this.getActiveLinkEl(editingElement);
        const activePaneEl = this.getActivePaneEl(editingElement);
        const nextActiveLinkEl =
            activeLinkEl.parentElement.nextElementSibling?.firstElementChild ||
            this.getNavLinkEls(editingElement)[0];
        const nextActivePaneEl =
            activePaneEl.nextElementSibling || this.getPaneEls(editingElement)[0];

        this.showTab(nextActiveLinkEl, nextActivePaneEl);
        this.dependencies.remove.removeElement(activeLinkEl.parentElement);
        this.dependencies.remove.removeElement(activePaneEl);
    }

    onNormalize(root) {
        const tabsEls = root.querySelectorAll("section.s_tabs");
        for (const tabsEl of tabsEls) {
            this.generateUniqueIDs(tabsEl);
        }
    }

    generateUniqueIDs(editingElement) {
        const navLinkEls = this.getNavLinkEls(editingElement);
        const ids = new Set([...navLinkEls].map((el) => el.id));
        const hasClonedTab = ids.size !== navLinkEls.length;
        const hasClonedSnippet =
            this.document.querySelectorAll(`#${[...ids].join(", #")}`).length !== navLinkEls.length;
        if (!hasClonedTab && !hasClonedSnippet) {
            return;
        }

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
registry.category("website-plugins").add(NavTabsPlugin.id, NavTabsPlugin);

class NavTabsHeaderMiddleButtons extends Component {
    static template = "html_builder.NavTabsHeaderMiddleButtons";
    static props = {
        addItem: Function,
        removeItem: Function,
    };

    setup() {
        this.state = useDomState((editingElement) => ({
            tabEls: editingElement.querySelectorAll(".s_tabs_nav .nav-item"),
        }));

        this.callOperation = useOperation();
    }

    addItem() {
        this.callOperation(() => {
            this.props.addItem(this.env.getEditingElement());
        });
    }

    removeItem() {
        this.callOperation(() => {
            this.props.removeItem(this.env.getEditingElement());
        });
    }
}
