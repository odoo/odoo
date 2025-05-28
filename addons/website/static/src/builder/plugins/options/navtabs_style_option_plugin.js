import { SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class NavTabsStyleOptionPlugin extends Plugin {
    static id = "navTabsOptionStyle";
    resources = {
        builder_options: [
            withSequence(SNIPPET_SPECIFIC_END, {
                template: "website.NavTabsStyleOption",
                selector: ".s_tabs",
                applyTo: ".s_tabs_main",
            }),
            withSequence(SNIPPET_SPECIFIC_END, {
                template: "website.NavTabsImagesStyleOption",
                selector: ".s_tabs_images",
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
                isApplied: ({ editingElement, value }) => {
                    const classList = this.getNavEl(editingElement).classList;
                    const containsFlexColumn =
                        classList.contains("flex-sm-column") ||
                        classList.contains("flex-md-column");
                    return value === "vertical" ? containsFlexColumn : !containsFlexColumn;
                },
                apply: ({ editingElement, value }) => {
                    this.applyDirection(editingElement, value);
                },
            },
        };
    }

    applyDirection(editingElement, direction) {
        // s_tabs_images use flex-md classes, while s_tabs use flex-sm classes
        const isTabsImages = editingElement
            .closest(".s_tabs_common")
            .classList.contains("s_tabs_images");

        const isVertical = direction === "vertical";
        const navEl = this.getNavEl(editingElement);

        editingElement.classList.toggle("row", isVertical);
        editingElement.classList.toggle("s_col_no_resize", isVertical);
        editingElement.classList.toggle("s_col_no_bgcolor", isVertical);
        navEl.classList.toggle(isTabsImages ? "flex-md-column" : "flex-sm-column", isVertical);
        editingElement
            .querySelectorAll(".s_tabs_nav > .nav-link")
            .forEach((linkEl) => linkEl.classList.toggle("py-2", isVertical));
        editingElement
            .querySelector(".s_tabs_nav")
            .classList.toggle(isTabsImages ? "col-md-3" : "col-sm-3", isVertical);
        editingElement
            .querySelector(".s_tabs_content")
            .classList.toggle(isTabsImages ? "col-md-9" : "col-sm-9", isVertical);

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
