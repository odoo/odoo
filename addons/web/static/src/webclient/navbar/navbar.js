/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useEffect, useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";
import { ErrorHandler, NotUpdatable } from "@web/core/utils/components";

const { Component, hooks } = owl;
const { useExternalListener, useRef } = hooks;
const systrayRegistry = registry.category("systray");

export class MenuDropdown extends Dropdown {
    setup() {
        super.setup();
        useEffect(
            () => {
                if (this.props.xmlid) {
                    this.togglerRef.el.dataset.menuXmlid = this.props.xmlid;
                }
            },
            () => []
        );
    }
}
MenuDropdown.props.xmlid = {
    type: String,
    optional: true,
};

export class MenuItem extends DropdownItem {
    setup() {
        super.setup();
        useEffect(
            () => {
                if (this.props.payload.id) {
                    this.el.dataset.section = this.props.payload.id;
                }
                if (this.props.payload.xmlid) {
                    this.el.dataset.menuXmlid = this.props.payload.xmlid;
                }
            },
            () => []
        );
    }
}

export class NavBar extends Component {
    setup() {
        this.currentAppSectionsExtra = [];
        this.actionService = useService("action");
        this.menuService = useService("menu");
        this.appSubMenus = useRef("appSubMenus");
        const debouncedAdapt = debounce(this.adapt.bind(this), 250);
        useExternalListener(window, "resize", debouncedAdapt);
    }

    mounted() {
        this.adapt();
        const renderAndAdapt = async () => {
            await this.render();
            await this.adapt();
        };
        systrayRegistry.on("UPDATE", this, renderAndAdapt);
        this.env.bus.on("MENUS:APP-CHANGED", this, renderAndAdapt);
    }

    willUnmount() {
        systrayRegistry.off("UPDATE", this);
        this.env.bus.off("MENUS:APP-CHANGED", this);
    }

    handleItemError(error, item) {
        // remove the faulty component
        item.isDisplayed = () => false;
        Promise.resolve().then(() => {
            throw error;
        });
    }

    get currentApp() {
        return this.menuService.getCurrentApp();
    }

    get currentAppSections() {
        return (
            (this.currentApp && this.menuService.getMenuAsTree(this.currentApp.id).childrenTree) ||
            []
        );
    }

    get systrayItems() {
        return systrayRegistry
            .getEntries()
            .map(([key, value]) => ({ key, ...value }))
            .filter((item) => ("isDisplayed" in item ? item.isDisplayed(this.env) : true))
            .reverse();
    }

    /**
     * Adapt will check the available width for the app sections to get displayed.
     * If not enough space is available, it will replace by a "more" menu
     * the least amount of app sections needed trying to fit the width.
     *
     * NB: To compute the widths of the actual app sections, a render needs to be done upfront.
     *     By the end of this method another render may occur depending on the adaptation result.
     */
    async adapt() {
        if (!this.el) {
            // currently, the promise returned by 'render' is resolved at the end of
            // the rendering even if the component has been destroyed meanwhile, so we
            // may get here and have this.el unset
            return;
        }

        // ------- Initialize -------
        // Get the sectionsMenu
        const sectionsMenu = this.appSubMenus.el;
        if (!sectionsMenu) {
            // No need to continue adaptations if there is no sections menu.
            return;
        }

        // Save initial state to further check if new render has to be done.
        const initialAppSectionsExtra = this.currentAppSectionsExtra;
        const firstInitialAppSectionExtra = [...initialAppSectionsExtra].shift();
        const initialAppId = firstInitialAppSectionExtra && firstInitialAppSectionExtra.appID;

        // Restore (needed to get offset widths)
        const sections = [
            ...sectionsMenu.querySelectorAll(":scope > *:not(.o_menu_sections_more)"),
        ];
        for (const section of sections) {
            section.classList.remove("d-none");
        }
        this.currentAppSectionsExtra = [];

        // ------- Check overflowing sections -------
        const sectionsAvailableWidth = sectionsMenu.offsetWidth;
        const sectionsTotalWidth = sections.reduce((sum, s) => sum + s.offsetWidth, 0);
        if (sectionsAvailableWidth < sectionsTotalWidth) {
            // Sections are overflowing
            // Initial width is harcoded to the width the more menu dropdown will take
            let width = 46;
            for (const section of sections) {
                if (sectionsAvailableWidth < width + section.offsetWidth) {
                    // Last sections are overflowing
                    const overflowingSections = sections.slice(sections.indexOf(section));
                    overflowingSections.forEach((s) => {
                        // Hide from normal menu
                        s.classList.add("d-none");
                        // Show inside "more" menu
                        const sectionId =
                            s.dataset.section ||
                            s.querySelector("[data-section]").getAttribute("data-section");
                        const currentAppSection = this.currentAppSections.find(
                            (appSection) => appSection.id.toString() === sectionId
                        );
                        this.currentAppSectionsExtra.push(currentAppSection);
                    });
                    break;
                }
                width += section.offsetWidth;
            }
        }

        // ------- Final rendering -------
        const firstCurrentAppSectionExtra = [...this.currentAppSectionsExtra].shift();
        const currentAppId = firstCurrentAppSectionExtra && firstCurrentAppSectionExtra.appID;
        if (
            initialAppSectionsExtra.length === this.currentAppSectionsExtra.length &&
            initialAppId === currentAppId
        ) {
            // Do not render if more menu items stayed the same.
            return;
        }
        return this.render();
    }

    onNavBarDropdownItemSelection(ev) {
        const { payload: menu } = ev.detail;
        if (menu) {
            this.menuService.selectMenu(menu);
        }
    }

    getMenuItemHref(payload) {
        const parts = [`menu_id=${payload.id}`];
        if (payload.action) {
            parts.push(`action=${payload.action.split(",")[1]}`);
        }
        return "#" + parts.join("&");
    }
}
NavBar.template = "web.NavBar";
NavBar.components = { MenuDropdown, MenuItem, NotUpdatable, ErrorHandler };
