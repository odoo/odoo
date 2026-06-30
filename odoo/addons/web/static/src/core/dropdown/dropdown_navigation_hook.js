/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { browser } from "../browser/browser";
import { localization } from "@web/core/l10n/localization";
import { scrollTo } from "../utils/scrolling";

import { useChildSubEnv, useComponent, useEffect, useRef } from "@odoo/owl";
import { ACCORDION } from "@web/core/dropdown/accordion_item";

/**
 * @typedef {{
 *  el: HTMLElement,
 *  isActive: boolean,
 *  makeOnlyActive: ()=>void,
 *  navTarget: HTMLElement,
 *  isSubDropdown: boolean,
 *  isSubDropdownOpen: boolean,
 *  closeSubDropdown: ()=>void,
 *  openSubDropdown: (immediate?:boolean)=>void,
 * }} MenuElement
 */

const ACTIVE_MENU_ELEMENT_CLASS = "focus";
const MENU_ELEMENTS_SELECTORS = [
    ":scope > .dropdown-item",
    ":scope > .dropdown",
    ":scope > .o_accordion > .dropdown-item",
    ":scope > .o_accordion > .o_accordion_values > .dropdown-item",
    ":scope > .o_dropdown_container > .dropdown-item",
    ":scope > .o_dropdown_container > .dropdown",
    ":scope > .o_dropdown_container > .o_accordion > .dropdown-item",
    ":scope > .o_dropdown_container > .o_accordion > .o_accordion_values > .dropdown-item",
];
const NEXT_ACTIVE_INDEX_FNS = {
    FIRST: () => 0,
    LAST: (list) => list.length - 1,
    NEXT: (list, prevActiveIndex) => (prevActiveIndex + 1) % list.length,
    PREV: (list, prevActiveIndex) => (prevActiveIndex <= 0 ? list.length : prevActiveIndex) - 1,
};

export function useDropdownNavigation() {
    /** @type {import("./dropdown").Dropdown} */
    const comp = useComponent();

    // As this navigation hook relies on clicking ".dropdown-toggle" elements,
    // it is incompatible with a toggler="parent" strategy for subdropdowns.
    if (comp.parentDropdown && comp.props.toggler === "parent") {
        throw new Error("A nested Dropdown must use its standard toggler");
    }

    // Needed to avoid unwanted mouseclick behavior on a subdropdown toggler.
    const originalOnTogglerClick = comp.onTogglerClick.bind(comp);
    comp.onTogglerClick = (ev) => {
        if (comp.parentDropdown && !ev.__fromDropdownNavigation) {
            return;
        }
        originalOnTogglerClick();
    };

    // Needed to avoid unwanted mouseenter behavior on a subdropdown toggler.
    const originalOnTogglerMouseEnter = comp.onTogglerMouseEnter.bind(comp);
    comp.onTogglerMouseEnter = () => {
        if (comp.parentDropdown) {
            return;
        }
        originalOnTogglerMouseEnter();
    };

    // Needed to avoid unwanted selection when the mouse pointer is not in use
    // but still somewhere in the middle of the dropdown menu list.
    let mouseSelectionActive = true;

    // Set up menu elements logic ----------------------------------------------
    const menuRef = useRef("menuRef");
    /** @type {MenuElement[]} */
    let menuElements = [];

    let cleanupMenuElements;
    const refreshMenuElements = () => {
        if (!comp.state.open) {
            return;
        }
        // Prepare MenuElements
        const addedListeners = [];
        /** @type {NodeListOf<HTMLElement>} */
        const queryResult = menuRef.el.querySelectorAll(MENU_ELEMENTS_SELECTORS.join());
        for (const el of queryResult) {
            const isSubDropdown = el.classList.contains("dropdown");
            const isSubDropdownOpen = () => el.classList.contains("show");
            const navTarget = isSubDropdown ? el.querySelector(":scope > .dropdown-toggle") : el;
            let subDropdownTimeout;
            const closeSubDropdown = () => {
                browser.clearTimeout(subDropdownTimeout);
                subDropdownTimeout = browser.setTimeout(() => {
                    if (isSubDropdownOpen()) {
                        const ev = new MouseEvent("click", { bubbles: false });
                        ev.__fromDropdownNavigation = true;
                        navTarget.dispatchEvent(ev);
                    }
                }, 200);
            };
            const openSubDropdown = (immediate = false) => {
                browser.clearTimeout(subDropdownTimeout);
                subDropdownTimeout = browser.setTimeout(
                    () => {
                        if (!isSubDropdownOpen()) {
                            const ev = new MouseEvent("click", { bubbles: false });
                            ev.__fromDropdownNavigation = true;
                            navTarget.dispatchEvent(ev);
                        }
                    },
                    immediate ? 0 : 200
                );
            };
            const makeOnlyActive = () => {
                // Make all others inactive
                for (const menuElement of menuElements) {
                    if (menuElement.el === el) {
                        continue;
                    }
                    menuElement.navTarget.classList.remove(ACTIVE_MENU_ELEMENT_CLASS);
                    if (menuElement.isSubDropdown) {
                        menuElement.closeSubDropdown();
                    }
                }
                // Make myself active
                navTarget.classList.add(ACTIVE_MENU_ELEMENT_CLASS);
                navTarget.focus();
            };

            /** @type {MenuElement} */
            const menuElement = {
                el,
                get isActive() {
                    return navTarget.classList.contains(ACTIVE_MENU_ELEMENT_CLASS);
                },
                makeOnlyActive,
                navTarget,
                get isSubDropdownOpen() {
                    return isSubDropdownOpen();
                },
                isSubDropdown,
                closeSubDropdown,
                openSubDropdown,
            };
            menuElements.push(menuElement);

            // Set up selection listeners
            const elementListeners = {
                mouseenter: () => {
                    if (!mouseSelectionActive) {
                        mouseSelectionActive = true;
                    } else {
                        makeOnlyActive();
                        if (isSubDropdown) {
                            openSubDropdown();
                        }
                    }
                },
            };
            for (const [eventType, listener] of Object.entries(elementListeners)) {
                navTarget.addEventListener(eventType, listener);
            }
            addedListeners.push([navTarget, elementListeners]);
        }
        cleanupMenuElements = () => {
            menuElements = [];
            mouseSelectionActive = true;

            // Clear mouse selection listeners
            for (const [navTarget, listeners] of addedListeners) {
                for (const [eventType, listener] of Object.entries(listeners)) {
                    navTarget.removeEventListener(eventType, listener);
                }
            }
        };
        return () => cleanupMenuElements();
    };

    useEffect(refreshMenuElements);

    // Set up nested accordion
    // This is needed in order to keep the parent dropdown
    // aware of the accordion menu elements when its state has changed.
    useChildSubEnv({
        [ACCORDION]: {
            accordionStateChanged: () => {
                cleanupMenuElements?.();
                refreshMenuElements();
            },
        },
    });

    // Set up active menu element helpers --------------------------------------
    /**
     * @returns {MenuElement|undefined}
     */
    const getActiveMenuElement = () => {
        return menuElements.find((menuElement) => menuElement.isActive);
    };

    /**
     * @param {MenuElement|keyof NEXT_ACTIVE_INDEX_FNS} menuElement
     */
    const setActiveMenuElement = (menuElement) => {
        if (menuElements.length) {
            if (typeof menuElement === "string") {
                const prevIndex = menuElements.indexOf(getActiveMenuElement());
                const nextIndex = NEXT_ACTIVE_INDEX_FNS[menuElement](menuElements, prevIndex);
                menuElement = menuElements[nextIndex];
            }
            menuElement.makeOnlyActive();
            scrollTo(menuElement.el, { scrollable: menuElement.el.parentElement });
        }
    };

    // Set up nested dropdowns - active first menu element behavior ------------
    useEffect(
        (open) => {
            // If we just opened and we are a subdropdown, make active our first menu element.
            if (open && comp.parentDropdown) {
                setActiveMenuElement("FIRST");
            }
        },
        () => [comp.state.open]
    );

    // Set up keyboard navigation ----------------------------------------------
    const hotkeyService = useService("hotkey");
    const closeAndRefocus = () => {
        const toFocus =
            comp.props.toggler === "parent"
                ? comp.rootRef.el.parentElement
                : comp.rootRef.el.querySelector(":scope > .dropdown-toggle");
        comp.close().then(() => {
            toFocus.focus();
        });
    };
    const closeSubDropdown = comp.parentDropdown ? closeAndRefocus : () => {};
    const openSubDropdown = () => {
        const menuElement = getActiveMenuElement();
        // Active menu element is a sub dropdown
        if (menuElement && menuElement.isSubDropdown) {
            menuElement.openSubDropdown(true);
        }
    };
    const selectActiveMenuElement = () => {
        const menuElement = getActiveMenuElement();
        if (menuElement) {
            if (menuElement.isSubDropdown) {
                menuElement.openSubDropdown(true);
            } else {
                menuElement.navTarget.click();
            }
        }
    };
    let hotkeyRemoves = [];
    const hotkeyCallbacks = {
        home: () => setActiveMenuElement("FIRST"),
        end: () => setActiveMenuElement("LAST"),
        tab: () => setActiveMenuElement("NEXT"),
        "shift+tab": () => setActiveMenuElement("PREV"),
        arrowdown: () => setActiveMenuElement("NEXT"),
        arrowup: () => setActiveMenuElement("PREV"),
        arrowleft: localization.direction === "rtl" ? openSubDropdown : closeSubDropdown,
        arrowright: localization.direction === "rtl" ? closeSubDropdown : openSubDropdown,
        enter: selectActiveMenuElement,
        escape: closeAndRefocus,
    };
    useEffect(
        (open) => {
            if (!open) {
                return;
            }
            // Subscribe keynav
            for (const [hotkey, callback] of Object.entries(hotkeyCallbacks)) {
                const callbackWrapper = () => {
                    const hasOpenedSubDropdown = menuElements.some((m) => m.isSubDropdownOpen);
                    // Leave priority to last opened sub dropdown
                    if (!hasOpenedSubDropdown) {
                        mouseSelectionActive = false;
                        callback.call(comp);
                    }
                };
                hotkeyRemoves.push(
                    hotkeyService.add(hotkey, callbackWrapper, { allowRepeat: true })
                );
            }
            return () => {
                // Unsubscribe keynav
                for (const removeHotkey of hotkeyRemoves) {
                    removeHotkey();
                }
                hotkeyRemoves = [];
            };
        },
        () => [comp.state.open]
    );
}
