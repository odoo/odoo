import {
    Component,
    onMounted,
    onPatched,
    onWillDestroy,
    proxy,
    signal,
    useEffect,
    useListener,
    usePlugin,
} from "@odoo/owl";
import { DebugModePlugin } from "@web/core/debug_mode_plugin";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownGroup } from "@web/core/dropdown/dropdown_group";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { OfflinePlugin } from "@web/core/offline/offline_plugin";
import { registry } from "@web/core/registry";
import { Transition } from "@web/core/transition";
import { ErrorHandler } from "@web/core/utils/components";
import { useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import { render } from "@web/owl2/utils";

const systrayRegistry = registry.category("systray");

const getBoundingClientRect = Element.prototype.getBoundingClientRect;

const SWIPE_ACTIVATION_THRESHOLD = 100;

const SECTION_MENU_TRAVEL_DURATION = 150;
/** How long a closed section menu still counts as the one being moved away from. */
const SECTION_MENU_TRAVEL_WINDOW = 150;

export class MenuDropdown extends Dropdown {}

export class NavBar extends Component {
    static template = "web.NavBar";
    static components = {
        Dropdown,
        DropdownItem,
        DropdownGroup,
        MenuDropdown,
        ErrorHandler,
        Transition,
    };
    root = signal.ref();
    appSubMenus = signal.ref();
    menuApps = signal.ref();

    debugMode = usePlugin(DebugModePlugin);

    setup() {
        this.currentAppSectionsExtra = [];
        this.actionService = useService("action");
        this.menuService = useService("menu");
        this.offlinePlugin = usePlugin(OfflinePlugin);
        this.pwa = useService("pwa");
        const debouncedAdapt = debounce(this.adapt.bind(this), 250);
        onWillDestroy(() => debouncedAdapt.cancel());
        useListener(window, "resize", debouncedAdapt);

        // The sections menu's width shrinks/grows when the breadcrumbs get longer or when
        // a systray item changes size (e.g. the offline item displaying "Working offline").
        let sectionsWidth = null;
        const sectionsObserver = new ResizeObserver(([entry]) => {
            const { inlineSize } = entry.borderBoxSize[0];
            if (inlineSize !== sectionsWidth) {
                sectionsWidth = inlineSize;
                debouncedAdapt();
            }
        });
        useEffect(() => {
            const sectionsMenu = this.appSubMenus();
            if (!sectionsMenu) {
                return;
            }
            // the initial observation notifies the current size: ignore it
            sectionsWidth = getBoundingClientRect.call(sectionsMenu).width;
            sectionsObserver.observe(sectionsMenu);
            return () => sectionsObserver.disconnect();
        });

        let adaptOnNextPatch = false;
        const renderAndAdapt = () => {
            adaptOnNextPatch = true;
            render(this);
        };

        useListener(systrayRegistry, "UPDATE", renderAndAdapt);
        useListener(this.env.bus, "MENUS:APP-CHANGED", renderAndAdapt);

        onMounted(() => {
            adaptOnNextPatch = false;
            this.adapt();
        });
        onPatched(() => {
            if (adaptOnNextPatch) {
                adaptOnNextPatch = false;
                this.adapt();
            }
        });

        this.state = proxy({
            isAllAppsMenuOpened: false,
            isAppMenuSidebarOpened: false,
        });
        this.ui = proxy(useService("ui"));
    }

    handleItemError(error, item) {
        // remove the faulty component
        item.isDisplayed = () => false;
        Promise.resolve().then(() => {
            throw error;
        });
    }

    get currentApp() {
        const app = this.menuService.getCurrentApp();
        if (app?.webIcon) {
            const [webIconClass, webIconColor, webIconBg] = app.webIcon.split(",");
            return {
                ...app,
                webIconClass,
                webIconColor,
                webIconBg,
            };
        }
        return app;
    }

    get currentAppSections() {
        return (
            (this.currentApp && this.menuService.getMenuAsTree(this.currentApp.id).childrenTree) ||
            []
        );
    }

    // This dummy setter is only here to prevent conflicts between the
    // Enterprise NavBar extension and the Website NavBar patch.
    set currentAppSections(_) {}

    get isScopedApp() {
        return this.pwa.isScopedApp;
    }

    get systrayItems() {
        return systrayRegistry
            .getEntries()
            .map(([key, value]) => ({ key, ...value }))
            .filter((item) => ("isDisplayed" in item ? item.isDisplayed(this.env) : true))
            .reverse();
    }

    // This dummy setter is only here to prevent conflicts between the
    // Enterprise NavBar extension and the Website NavBar patch.
    set systrayItems(_) {}

    /**
     * Adapt will check the available width for the app sections to get displayed.
     * If not enough space is available, it will replace by a "more" menu
     * the least amount of app sections needed trying to fit the width.
     *
     * NB: To compute the widths of the actual app sections, a render needs to be done upfront.
     *     By the end of this method another render may occur depending on the adaptation result.
     */
    async adapt() {
        if (!this.root()) {
            /** @todo do we still need this check? */
            // currently, the promise returned by 'render' is resolved at the end of
            // the rendering even if the component has been destroyed meanwhile, so we
            // may get here and have this.el unset
            return;
        }

        // ------- Initialize -------
        // Get the sectionsMenu
        const sectionsMenu = this.appSubMenus();
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
        // use getBoundingClientRect to get unrounded values for width in order to avoid rounding problem
        // with offsetWidth.
        const sectionsAvailableWidth = getBoundingClientRect.call(sectionsMenu).width;
        const sectionsTotalWidth = sections.reduce(
            (sum, s) => sum + getBoundingClientRect.call(s).width,
            0
        );
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
        this.render();
    }

    render() {
        render(this);
    }

    onNavBarDropdownItemSelection(menu) {
        if (menu) {
            this.menuService.selectMenu(menu);
        }
    }

    /**
     * Slides a section's menu in from where the previous one stood, so that
     * moving across the sections reads as a single menu travelling. Each
     * section has its own popover, so the move has to be replayed by hand.
     *
     * @param {HTMLElement} el
     * @param {number} sectionId
     * @param {{ top: number, left: number }} solution
     */
    onSectionMenuPositioned(el, sectionId, solution) {
        const previous = this.lastSectionMenu;
        // The solution rather than a measurement: every section menu resolves
        // against the same containing block, and it is free of the travelling
        // transform a `getBoundingClientRect` would pick up mid-animation.
        this.lastSectionMenu = { sectionId, top: solution.top, left: solution.left };
        // Repositioning the same menu (scroll, resize) is not a move.
        if (!previous || previous.sectionId === sectionId) {
            return;
        }
        // A section only travels from one that was still on screen. Opening a
        // menu long after the last one closed is a plain appearance.
        if (previous.closedAt && Date.now() - previous.closedAt > SECTION_MENU_TRAVEL_WINDOW) {
            return;
        }
        const dx = previous.left - solution.left;
        const dy = previous.top - solution.top;
        if (!dx && !dy) {
            return;
        }
        el.animate(
            { transform: [`translate(${dx}px, ${dy}px)`, "translate(0, 0)"] },
            { duration: SECTION_MENU_TRAVEL_DURATION, easing: "ease-out" }
        );
    }

    /**
     * @param {boolean} isOpen
     * @param {number} sectionId
     */
    onSectionMenuStateChanged(isOpen, sectionId) {
        // Stamped rather than dropped: hovering a sibling closes this menu
        // before the next one is positioned, and the next one still needs to
        // know where this one stood.
        if (!isOpen && this.lastSectionMenu?.sectionId === sectionId) {
            this.lastSectionMenu.closedAt = Date.now();
        }
    }

    getMenuItemHref(payload) {
        const url = `/odoo/${payload.actionPath || "action-" + payload.actionID}`;
        const mode = this.debugMode.toString();
        if (mode) {
            return `${url}?debug=${mode}`;
        }
        return url;
    }

    _closeAppMenuSidebar() {
        this.state.isAllAppsMenuOpened = false;
        this.state.isAppMenuSidebarOpened = false;
    }
    _openAppMenuSidebar() {
        this.state.isAppMenuSidebarOpened = !this.state.isAppMenuSidebarOpened;
    }

    _isAvailable(menu) {
        return (
            !this.offlinePlugin.isOffline() ||
            !menu.actionID ||
            this.offlinePlugin.isAvailableOffline(menu.actionID)
        );
    }

    onAllAppsBtnClick() {
        this.state.isAllAppsMenuOpened = !this.state.isAllAppsMenuOpened;
    }
    async _onMenuClicked(menu) {
        await this.menuService.selectMenu(menu);
        this._closeAppMenuSidebar();
    }
    _onSwipeStart(ev) {
        this.swipeStartX = ev.changedTouches[0].clientX;
    }
    _onSwipeEnd(ev) {
        if (!this.swipeStartX) {
            return;
        }
        const deltaX = this.swipeStartX - ev.changedTouches[0].clientX;
        if (deltaX < SWIPE_ACTIVATION_THRESHOLD) {
            return;
        }
        this._closeAppMenuSidebar();
        this.swipeStartX = null;
    }
}
