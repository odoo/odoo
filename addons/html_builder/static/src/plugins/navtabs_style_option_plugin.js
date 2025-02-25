import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class NavTabsStyleOptionPlugin extends Plugin {
    static id = "navTabsOptionStyle";
    resources = {
        builder_options: [
            withSequence(50, {
                template: "html_builder.NavTabsStyleOption",
                selector: "section",
                applyTo: ".s_tabs_main",
            }),
        ],
        builder_actions: this.getActions(),
    };

    setup() {
        this.tabsTabsClasses = [
            "card-header",
            "px-0",
            "border-0",
            "overflow-x-auto",
            "overflow-y-hidden",
        ];
        this.navTabsClasses = ["card-header-tabs", "mx-0", "px-2", "border-bottom"];
        this.tabsBtnClasses = ["d-flex", "rounded"];
        this.navBtnClasses = ["d-inline-flex", "nav-pills", "p-2"];
    }

    getNavEl(editingElement) {
        return editingElement.querySelector(".s_tabs_nav .nav");
    }

    getActions() {
        const getTabsEl = (editingElement) => editingElement.querySelector(".s_tabs_nav");
        return {
            setStyle: {
                isApplied: ({ editingElement, value }) => {
                    const navEl = this.getNavEl(editingElement);
                    // 'nav-buttons' also applies 'nav-pills'
                    if (navEl.classList.contains("nav-buttons")) {
                        return value === "nav-buttons";
                    }
                    return navEl.classList.contains(value);
                },
                apply: ({ editingElement, value }) => {
                    const isTabs = value === "nav-tabs";
                    const isBtns = value === "nav-buttons";
                    const tabsEl = getTabsEl(editingElement);
                    const navEl = this.getNavEl(editingElement);

                    if (isTabs || isBtns) {
                        this.applyDirection(editingElement, "horizontal");
                    }

                    if (isTabs) {
                        tabsEl.classList.add(...this.tabsTabsClasses);
                        navEl.classList.add(...this.navTabsClasses);
                    } else if (isBtns) {
                        tabsEl.classList.add(...this.tabsBtnClasses);
                        navEl.classList.add(...this.navBtnClasses);
                    }
                    navEl.classList.add(value);

                    editingElement.classList.toggle("card", isTabs);
                    tabsEl.classList.toggle("mb-3", !isTabs);
                    navEl.classList.toggle("overflow-x-auto", !isTabs);
                    navEl.classList.toggle("overflow-y-hidden", !isTabs);
                    editingElement.querySelector(".s_tabs_content").classList.toggle("p-3", isTabs);
                },
                clean: ({ editingElement, value }) => {
                    const isTabs = value === "nav-tabs";
                    const isBtns = value === "nav-buttons";
                    const tabsEl = getTabsEl(editingElement);
                    const navEl = this.getNavEl(editingElement);

                    if (isTabs) {
                        tabsEl.classList.remove(...this.tabsTabsClasses);
                        navEl.classList.remove(...this.navTabsClasses);
                    } else if (isBtns) {
                        tabsEl.classList.remove(...this.tabsBtnClasses);
                        navEl.classList.remove(...this.navBtnClasses);
                    }
                    navEl.classList.remove(value);
                },
            },
            setDirection: {
                isApplied: ({ editingElement, value }) =>
                    this.getNavEl(editingElement).classList.contains("flex-sm-column") ===
                    (value === "vertical"),
                apply: ({ editingElement, value }) => {
                    this.applyDirection(editingElement, value);
                },
            },
        };
    }

    applyDirection(editingElement, direction) {
        const isVertical = direction === "vertical";
        const navEl = this.getNavEl(editingElement);

        editingElement.classList.toggle("row", isVertical);
        editingElement.classList.toggle("s_col_no_resize", isVertical);
        editingElement.classList.toggle("s_col_no_bgcolor", isVertical);
        navEl.classList.toggle("flex-sm-column", isVertical);
        editingElement
            .querySelectorAll(".s_tabs_nav > .nav-link")
            .forEach((linkEl) => linkEl.classList.toggle("py-2", isVertical));
        editingElement.querySelector(".s_tabs_nav").classList.toggle("col-sm-3", isVertical);
        editingElement.querySelector(".s_tabs_content").classList.toggle("col-sm-9", isVertical);

        // Clean incompatible leftover classes in vertical mode.
        // See "Fill and Justify" and "Alignment" options.
        if (isVertical) {
            navEl.classList.remove(
                "nav-fill",
                "nav-justified",
                "justify-content-center",
                "justify-content-end",
                "ms-auto",
                "mx-auto"
            );
        }
    }
}

registry.category("website-plugins").add(NavTabsStyleOptionPlugin.id, NavTabsStyleOptionPlugin);
