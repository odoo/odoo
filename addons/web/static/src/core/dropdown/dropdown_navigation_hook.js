/** @odoo-module */

import { useEffect, useService } from "@web/core/utils/hooks";
import { browser } from "../browser/browser";
import { scrollTo } from "../utils/scrolling";

/**
 * @typedef {{
 *  el: HTMLElement,
 *  isActive: boolean,
 *  makeOnlyActive: ()=>void,
 *  isSubDropdown: boolean,
 *  isSubDropdownOpen: boolean,
 *  closeSubDropdown: ()=>void,
 *  openSubDropdown: (immediate?:boolean)=>void,
 * }} MenuElement
 */

const { hooks } = owl;
const { useComponent, useRef } = hooks;

const ACTIVE_MENU_ELEMENT_CLASS = "active";
const MENU_ELEMENTS_SELECTORS = [":scope > li.o_dropdown_item", ":scope > li.o_dropdown"];
const NEXT_ACTIVE_INDEX_FNS = {
    FIRST: () => 0,
    LAST: (list) => list.length - 1,
    NEXT: (list, prevActiveIndex) => (prevActiveIndex + 1) % list.length,
    PREV: (list, prevActiveIndex) => (prevActiveIndex <= 0 ? list.length : prevActiveIndex) - 1,
};

export function useDropdownNavigation() {
    /** @type {import("./dropdown").Dropdown} */
    const comp = useComponent();

    // As this navigation hook relies on clicking ".o_dropdown_toggler" elements,
    // it is incompatible with a toggler="parent" strategy for subdropdowns.
    if (comp.hasParentDropdown && comp.props.toggler === "parent") {
        throw new Error("A nested Dropdown must use its standard toggler");
    }

    // Needed to avoid unwanted selection when the mouse pointer is not in use
    // but still somewhere in the middle of the dropdown menu list.
    let mouseSelectionActive = true;

    // Set up menu elements logic ----------------------------------------------
    const menuRef = useRef("menuRef");
    /** @type {MenuElement[]} */
    let menuElements = [];
    useEffect(
        (open) => {
            if (!open) {
                return;
            }
            // Prepare MenuElements
            const addedListeners = [];
            /** @type {NodeListOf<HTMLElement>} */
            const queryResult = menuRef.el.querySelectorAll(MENU_ELEMENTS_SELECTORS.join());
            for (const el of queryResult) {
                const isSubDropdown = el.classList.contains("o_dropdown");
                const isSubDropdownOpen = () => el.classList.contains("o-dropdown--open");
                const togglerClick = () => {
                    const toggler = el.querySelector(":scope > .o_dropdown_toggler");
                    if (toggler) {
                        toggler.dispatchEvent(new MouseEvent("click", { bubbles: false }));
                    }
                };
                let subDropdownTimeout;
                const closeSubDropdown = () => {
                    browser.clearTimeout(subDropdownTimeout);
                    subDropdownTimeout = browser.setTimeout(() => {
                        if (isSubDropdownOpen()) {
                            togglerClick();
                        }
                    }, 200);
                };
                const openSubDropdown = (immediate = false) => {
                    browser.clearTimeout(subDropdownTimeout);
                    subDropdownTimeout = browser.setTimeout(
                        () => {
                            if (!isSubDropdownOpen()) {
                                togglerClick();
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
                        menuElement.el.classList.remove(ACTIVE_MENU_ELEMENT_CLASS);
                        if (menuElement.isSubDropdown) {
                            menuElement.closeSubDropdown();
                        }
                    }
                    // Make myself active
                    el.classList.add(ACTIVE_MENU_ELEMENT_CLASS);
                };

                /** @type {MenuElement} */
                const menuElement = {
                    el,
                    get isActive() {
                        return el.classList.contains(ACTIVE_MENU_ELEMENT_CLASS);
                    },
                    makeOnlyActive,
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
                    click: makeOnlyActive,
                    mouseenter: () => {
                        if (!mouseSelectionActive) {
                            mouseSelectionActive = true;
                        } else {
                            menuElement.makeOnlyActive();
                            if (isSubDropdown) {
                                openSubDropdown();
                            }
                        }
                    },
                };
                for (const [eventType, listener] of Object.entries(elementListeners)) {
                    menuElement.el.addEventListener(eventType, listener);
                }
                addedListeners.push([menuElement, elementListeners]);
            }
            return () => {
                menuElements = [];
                mouseSelectionActive = true;

                // Clear mouse selection listeners
                for (const [menuElement, listeners] of addedListeners) {
                    for (const [eventType, listener] of Object.entries(listeners)) {
                        menuElement.el.removeEventListener(eventType, listener);
                    }
                }
            };
        },
        () => [comp.state.open]
    );

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
            scrollTo(menuElement.el, menuElement.el.parentElement);
        }
    };

    // Set up nested dropdowns - active first menu element behavior ------------
    useEffect(
        (open) => {
            // If we just opened and we are a subdropdown, make active our first menu element.
            if (open && comp.hasParentDropdown) {
                setActiveMenuElement("FIRST");
            }
        },
        () => [comp.state.open]
    );

    // Set up keyboard navigation ----------------------------------------------
    const hotkeyService = useService("hotkey");
    let hotkeyRemoves = [];
    const hotkeyCallbacks = {
        home: () => setActiveMenuElement("FIRST"),
        end: () => setActiveMenuElement("LAST"),
        tab: () => setActiveMenuElement("NEXT"),
        "shift+tab": () => setActiveMenuElement("PREV"),
        arrowdown: () => setActiveMenuElement("NEXT"),
        arrowup: () => setActiveMenuElement("PREV"),
        arrowleft: () => {
            if (comp.hasParentDropdown) {
                comp.close();
            }
        },
        arrowright: () => {
            const menuElement = getActiveMenuElement();
            // Active menu element is a sub dropdown
            if (menuElement && menuElement.isSubDropdown) {
                menuElement.openSubDropdown(true);
            }
        },
        enter: () => {
            const menuElement = getActiveMenuElement();
            if (menuElement) {
                menuElement.el.click();
            }
        },
        escape: comp.close,
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
