import { useEffect, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { scrollTo } from "@web/core/utils/scrolling";
import { debounce, throttleForAnimation } from "@web/core/utils/timing";

const ACTIVE_ELEMENT_CLASS = "focus";
const throttledElementFocus = throttleForAnimation((el) => el?.focus());

function focusElement(el) {
    throttledElementFocus.cancel();
    throttledElementFocus(el);
}

class NavigationItem {
    constructor({ index, el, setActiveItem, options }) {
        this.index = index;
        this.options = options;
        this.setActiveItem = setActiveItem;

        this.el = el;
        if (options.shouldFocusChildInput) {
            const subInput = el.querySelector(":scope input, :scope button, :scope textarea");
            this.target = subInput || el;
        } else {
            this.target = el;
        }

        const focus = () => this.focus(true);
        const onMouseEnter = (ev) => this.onMouseEnter(ev);

        this.target.addEventListener("focus", focus);
        this.target.addEventListener("mouseenter", onMouseEnter);
        this.removeListeners = () => {
            this.target.removeEventListener("focus", focus);
            this.target.removeEventListener("mouseenter", onMouseEnter);
        };
    }

    select() {
        this.focus();
        this.target.click();
    }

    focus(skipRealFocus = false) {
        scrollTo(this.target);
        this.setActiveItem(this.index, this);
        this.target.classList.add(ACTIVE_ELEMENT_CLASS);

        if (!skipRealFocus && !this.options.virtualFocus) {
            focusElement(this.target);
        }
    }

    defocus() {
        this.target.classList.remove(ACTIVE_ELEMENT_CLASS);
    }

    onMouseEnter() {
        this.focus(true);
        this.options.onMouseEnter?.(this);
    }
}

class Navigator {
    /**
     * @param {*} containerRef
     * @param {NavigationOptions} options
     */
    constructor(containerRef, options, hotkeyService) {
        this.enabled = false;
        this.containerRef = containerRef;

        const focusAt = (increment) => {
            const isFocused = this.activeItem?.el.isConnected;
            const index = this.currentActiveIndex + increment;
            if (isFocused && index >= 0) {
                return this.items[index % this.items.length]?.focus();
            } else if (!isFocused && increment >= 0) {
                return this.items[0]?.focus();
            } else {
                return this.items.at(-1)?.focus();
            }
        };

        this.options = {
            shouldFocusChildInput: true,
            virtualFocus: false,
            itemsSelector: ":scope .o-navigable",
            focusInitialElementOnDisabled: () => true,
            ...options,

            hotkeys: {
                home: (index, items) => items[0]?.focus(),
                end: (index, items) => items.at(-1)?.focus(),
                tab: () => focusAt(+1),
                "shift+tab": () => focusAt(-1),
                arrowdown: () => focusAt(+1),
                arrowup: () => focusAt(-1),
                enter: (index, items) => {
                    const item = items[index] || items[0];
                    item?.select();
                },
                ...(options?.hotkeys || {}),
            },
        };

        /**@type {Array<NavigationItem>} */
        this.items = [];

        /**@type {NavigationItem|undefined}*/
        this.activeItem = undefined;
        this.currentActiveIndex = -1;

        this.initialFocusElement = undefined;
        this.debouncedUpdate = debounce(() => this.update(), 100);

        this.hotkeyRemoves = [];
        this.hotkeyService = hotkeyService;

        this.allowedInEditableHotkeys = ["arrowup", "arrowdown", "enter", "tab", "shift+tab"];
    }

    enable() {
        if (!this.containerRef.el || this.targetObserver) {
            return;
        }

        for (const [hotkey, callback] of Object.entries(this.options.hotkeys)) {
            if (!callback) {
                continue;
            }

            this.hotkeyRemoves.push(
                this.hotkeyService.add(
                    hotkey,
                    () => callback(this.currentActiveIndex, this.items),
                    {
                        allowRepeat: true,
                        bypassEditableProtection: this.allowedInEditableHotkeys.includes(hotkey),
                    }
                )
            );
        }

        this.targetObserver = new MutationObserver(() => this.debouncedUpdate());
        this.targetObserver.observe(this.containerRef.el, {
            childList: true,
            subtree: true,
        });

        this.initialFocusElement = document.activeElement;
        this.currentActiveIndex = -1;
        this.update();

        if (this.options.onEnabled) {
            this.options.onEnabled(this.items);
        } else if (this.items.length > 0) {
            this.items[0]?.focus();
        }

        this.enabled = true;
    }

    disable() {
        if (!this.enabled) {
            return;
        }

        if (this.targetObserver) {
            this.targetObserver.disconnect();
            this.targetObserver = undefined;
        }

        this.clearItems();
        for (const removeHotkey of this.hotkeyRemoves) {
            removeHotkey();
        }
        this.hotkeyRemoves = [];

        if (this.options.focusInitialElementOnDisabled()) {
            focusElement(this.initialFocusElement);
        }

        this.enabled = false;
    }

    update() {
        if (!this.containerRef.el) {
            return;
        }
        const oldItemsLength = this.items.length;
        this.clearItems();

        const elements = [...this.containerRef.el.querySelectorAll(this.options.itemsSelector)];
        this.items = elements.map((el, index) => {
            return new NavigationItem({
                index,
                el,
                options: this.options,
                setActiveItem: (index, el) => this.setActiveItem(index, el),
            });
        });

        if (oldItemsLength != this.items.length && this.currentActiveIndex >= this.items.length) {
            this.items.at(-1)?.focus();
        }
    }

    setActiveItem(index, item) {
        if (this.activeItem) {
            this.activeItem.el.classList.remove(ACTIVE_ELEMENT_CLASS);
        }
        this.activeItem = item;
        this.currentActiveIndex = index;
    }

    clearItems() {
        for (const item of this.items) {
            item.removeListeners();
        }
        this.items = [];
    }
}

/**
 * @typedef {Object} NavigationOptions
 * @property {NavigationHotkeys} hotkeys
 * @property {Function} onEnabled
 * @property {Function} onMouseEnter
 * @property {Boolean} [virtualFocus=false] - If true, items are only visually
 * focused so the actual focus can be kept on another input.
 * @property {string} [itemsSelector=":scope .o-navigable"] - The selector used to get the list
 * of navigable elements.
 * @property {Function} focusInitialElementOnDisabled
 * @property {Boolean} [shouldFocusChildInput=false] - If true, elements like inputs or buttons
 * inside of the items are focused instead of the items themselves.
 */

/**
 * @typedef {{
 *  home: keyHandlerCallback|undefined,
 *  end: keyHandlerCallback|undefined,
 *  tab: keyHandlerCallback|undefined,
 *  "shift+tab": keyHandlerCallback|undefined,
 *  arrowup: keyHandlerCallback|undefined,
 *  arrowdown: keyHandlerCallback|undefined,
 *  enter: keyHandlerCallback|undefined,
 *  arrowleft: keyHandlerCallback|undefined,
 *  arrowright: keyHandlerCallback|undefined,
 *  escape: keyHandlerCallback|undefined,
 *  space: keyHandlerCallback|undefined,
 * }} NavigationHotkeys
 */

/**
 * Callback used to override the behaviour of a specific
 * key input.
 *
 * @callback keyHandlerCallback
 * @param {number} index                Current index.
 * @param {Array<NavigationItem>} items List of all navigation items.
 */

/**
 * @typedef NavigationHook
 * @method enable
 * @method disable
 */

/**
 * This hook adds keyboard navigation to items contained in an element.
 * It's purpose is to improve navigation in constrained context such
 * as dropdown and menus.
 *
 * This hook also has the following features:
 * - Hotkeys override and customization
 * - Navigation between inputs elements
 * - Optional virtual focus
 * - Focus on mouse enter
 *
 * @param {string|Object} containerRef
 * @param {NavigationOptions} options
 * @returns {NavigationHook}
 */
export function useNavigation(containerRef, options = {}) {
    const hotkeyService = useService("hotkey");
    containerRef = typeof containerRef === "string" ? useRef(containerRef) : containerRef;
    const navigator = new Navigator(containerRef, options, hotkeyService);

    useEffect(
        (container) => {
            if (container) {
                navigator.enable();
            } else if (navigator) {
                navigator.disable();
            }
        },
        () => [containerRef.el]
    );

    return {
        enable: () => navigator.enable(),
        disable: () => navigator.disable(),
    };
}
