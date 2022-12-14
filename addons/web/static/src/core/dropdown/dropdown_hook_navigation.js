/** @odoo-module **/

import { useEffect } from "@odoo/owl";
import { useService } from "../utils/hooks";
import { localization } from "../l10n/localization";

const ACTIVE_MENU_ELEMENT_CLASS = "focus";
const MENU_ELEMENTS_SELECTOR = ":scope > .dropdown-item, :scope > .dropdown";

export function useDropdownHookNavigation(dropdown) {
    let elements = [];
    let currentIndex = 0;

    useEffect(
        (menuEl) => {
            if (!menuEl) {
                return;
            }
            elements = Array.from(menuEl.querySelectorAll(MENU_ELEMENTS_SELECTOR));
            currentIndex = 0;
        },
        () => [dropdown.menuRef.el]
    );

    function setActive(activeElement) {
        for (const element of elements) {
            if (element === activeElement) {
                continue;
            }
            element.classList.remove(ACTIVE_MENU_ELEMENT_CLASS);
        }

        activeElement.classList.add(ACTIVE_MENU_ELEMENT_CLASS);
        activeElement.focus();
    }

    function setActiveMenuElement(index) {
        const m = elements.length;
        currentIndex = ((index % m) + m) % m;

        if (currentIndex >= 0 && currentIndex < elements.length) {
            setActive(elements[currentIndex]);
        }
    }

    function selectActiveMenuElement() {
        elements[currentIndex].click();
    }

    function openSubDropdown() {}
    function closeSubDropdown() {}
    function closeAndRefocus() {}

    const hotkeyCallbacks = {
        home: () => setActiveMenuElement(0),
        end: () => setActiveMenuElement(elements.length - 1),
        tab: () => setActiveMenuElement(currentIndex + 1),
        "shift+tab": () => setActiveMenuElement(currentIndex - 1),
        arrowdown: () => setActiveMenuElement(currentIndex + 1),
        arrowup: () => setActiveMenuElement(currentIndex - 1),
        arrowleft: localization.direction === "rtl" ? openSubDropdown : closeSubDropdown,
        arrowright: localization.direction === "rtl" ? closeSubDropdown : openSubDropdown,
        enter: () => selectActiveMenuElement(),
        escape: () => closeAndRefocus(),
    };

    const hotkeyService = useService("hotkey");
    let hotkeys = [];
    useEffect(
        (open) => {
            if (!open) {
                return;
            }
            // Subscribe keynav
            for (const [hotkey, callback] of Object.entries(hotkeyCallbacks)) {
                const removeHotkey = hotkeyService.add(hotkey, callback, { allowRepeat: true });
                hotkeys.push(removeHotkey);
            }

            return () => {
                // Unsubscribe keynav
                for (const removeHotkey of hotkeys) {
                    removeHotkey();
                }
                hotkeys = [];
            };
        },
        () => [dropdown.isOpen]
    );
}
