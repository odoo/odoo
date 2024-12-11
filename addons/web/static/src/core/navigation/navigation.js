import { useEffect, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { deepMerge } from "@web/core/utils/objects";
import { scrollTo } from "@web/core/utils/scrolling";
import { throttleForAnimation } from "@web/core/utils/timing";

export const ACTIVE_ELEMENT_CLASS = "focus";
const throttledFocus = throttleForAnimation((el) => el?.focus());

class NavigationItem {
    /**@type {number} */
    index = -1;

    /**
     * The container element
     * @type {Element}
     */
    el = undefined;

    /**
     * The actual "clicked" element, it can be the same
     * as @see el but will be the closest child input if
     * options.shouldFocusChildInput is true
     * @type {Element}
     */
    target = undefined;

    constructor({ index, el, setActiveItem, options }) {
        this.index = index;

        /**@private */
        this._options = options;

        /**@private*/
        this._setActiveItem = setActiveItem;

        this.el = el;
        if (this._options.shouldFocusChildInput) {
            const subInput = el.querySelector(":scope input, :scope button, :scope textarea");
            this.target = subInput || el;
        } else {
            this.target = el;
        }

        const onFocus = () => this.setActive(false);
        const onMouseEnter = () => this._onMouseEnter();

        this.target.addEventListener("focus", onFocus);
        this.target.addEventListener("mouseenter", onMouseEnter);

        /**@private*/
        this._removeListeners = () => {
            this.target.removeEventListener("focus", onFocus);
            this.target.removeEventListener("mouseenter", onMouseEnter);
        };
    }

    select() {
        this.setActive();
        this.target.click();
    }

    setActive(focus = true) {
        scrollTo(this.target);
        this._setActiveItem(this.index);
        this.target.classList.add(ACTIVE_ELEMENT_CLASS);

        if (focus && !this._options.virtualFocus) {
            throttledFocus.cancel();
            throttledFocus(this.target);
        }
    }

    /**
     * @private
     */
    _onMouseEnter() {
        this.setActive(false);
        this._options.onMouseEnter?.(this);
    }
}

class Navigator {
    /**@type {NavigationItem|undefined}*/
    activeItem = undefined;

    /**@type {number}*/
    activeItemIndex = -1;

    /**@type {Array<NavigationItem>}*/
    items = [];

    /**@private*/ _enabled = false;
    /**@private*/ _targetObserver = undefined;
    /**@private*/ _initialFocusElement = undefined;
    /**@private*/ _hotkeyRemoves = [];
    /**@private*/ _hotkeyService = undefined;

    /**
     * @param {*} containerRef
     * @param {NavigationOptions} options
     */
    constructor(containerRef, options, hotkeyService) {
        this.containerRef = containerRef;
        this._hotkeyService = hotkeyService;

        /**@private*/
        this._options = deepMerge(
            {
                shouldFocusChildInput: true,
                virtualFocus: false,
                itemsSelector: ":scope .o-navigable",
                focusInitialElementOnDisabled: () => true,

                hotkeys: {
                    home: () => this.items[0]?.setActive(),
                    end: () => this.items.at(-1)?.setActive(),
                    tab: {
                        callback: () => this.next(),
                        bypassEditableProtection: true,
                    },
                    "shift+tab": {
                        callback: () => this.previous(),
                        bypassEditableProtection: true,
                    },
                    arrowdown: {
                        callback: () => this.next(),
                        bypassEditableProtection: true,
                    },
                    arrowup: {
                        callback: () => this.previous(),
                        bypassEditableProtection: true,
                    },
                    enter: {
                        callback: () => {
                            const item = this.activeItem || this.items[0];
                            item?.select();
                        },
                        bypassEditableProtection: true,
                    },
                },
            },
            options
        );
    }

    /**
     * Returns true if the focus is on any of the navigable items
     * @type {boolean}
     */
    get isFocused() {
        return Boolean(this.activeItem?.el.isConnected);
    }

    next() {
        if (!this.isFocused) {
            this.items[0]?.setActive();
        } else {
            this.items[(this.activeItemIndex + 1) % this.items.length]?.setActive();
        }
    }

    previous() {
        const index = this.activeItemIndex - 1;
        if (!this.isFocused || index < 0) {
            this.items.at(-1)?.setActive();
        } else {
            this.items[index % this.items.length]?.setActive();
        }
    }

    /**
     * @private
     */
    _enable() {
        if (!this.containerRef.el || this._targetObserver) {
            return;
        }

        for (const [hotkey, hotkeyInfo] of Object.entries(this._options.hotkeys)) {
            if (!hotkeyInfo) {
                continue;
            }

            const isFunction = typeof hotkeyInfo === "function";
            const callback = isFunction ? hotkeyInfo : hotkeyInfo.callback;
            const isAvailable = hotkeyInfo?.isAvailable ?? (() => true);
            const bypassEditableProtection = hotkeyInfo?.bypassEditableProtection ?? false;

            this._hotkeyRemoves.push(
                this._hotkeyService.add(hotkey, () => callback(this), {
                    allowRepeat: true,
                    isAvailable: () => isAvailable(this),
                    bypassEditableProtection,
                })
            );
        }

        this._targetObserver = new MutationObserver(() => this._update());
        this._targetObserver.observe(this.containerRef.el, {
            childList: true,
            subtree: true,
        });

        this._initialFocusElement = document.activeElement;
        this.activeItemIndex = -1;
        this._update();

        if (this._options.onEnabled) {
            this._options.onEnabled(this.items);
        } else if (this.items.length > 0) {
            this.items[0]?.setActive();
        }

        this._enabled = true;
    }

    /**
     * @private
     */
    _disable() {
        if (!this._enabled) {
            return;
        }

        if (this._targetObserver) {
            this._targetObserver.disconnect();
            this._targetObserver = undefined;
        }

        this._clearItems();
        for (const removeHotkey of this._hotkeyRemoves) {
            removeHotkey();
        }
        this._hotkeyRemoves = [];

        if (this._options.focusInitialElementOnDisabled()) {
            throttledFocus.cancel();
            throttledFocus(this._initialFocusElement);
        }

        this._enabled = false;
    }

    /**
     * @private
     */
    _update() {
        if (!this.containerRef.el) {
            return;
        }
        const oldActiveItem = this.activeItem;
        const oldItemsLength = this.items.length;

        const elements = [...this.containerRef.el.querySelectorAll(this._options.itemsSelector)];
        if (this.items.length > elements.length) {
            this.items.splice(elements.length - this.items.length);
        }

        for (let i = 0; i < elements.length; i++) {
            const navItem = new NavigationItem({
                index: i,
                el: elements[i],
                options: this._options,
                setActiveItem: (index) => this._setActiveItem(index),
            });

            if (i >= this.items.length) {
                this.items.push(navItem);
            } else {
                this.items[i] = navItem;
            }
        }

        // Focus last item if some where removed
        if (oldItemsLength != this.items.length && this.activeItemIndex >= this.items.length) {
            this.items.at(-1)?.setActive();
        }
        // Focus closest item if the current active item has changed/was removed
        else if (
            this.activeItemIndex < this.items.length &&
            oldActiveItem !== this.items[this.activeItemIndex]
        ) {
            this.items[this.activeItemIndex]?.setActive();
        }
    }

    /**
     * @private
     */
    _setActiveItem(index) {
        if (this.activeItem) {
            this.activeItem.el.classList.remove(ACTIVE_ELEMENT_CLASS);
        }
        this.activeItem = this.items[index];
        this.activeItemIndex = index;
    }

    /**
     * @private
     */
    _clearItems() {
        for (const item of this.items) {
            item._removeListeners();
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
 *  home: hotkeyHandler|HotkeyOptions|undefined,
 *  end: hotkeyHandler|HotkeyOptions|undefined,
 *  tab: hotkeyHandler|HotkeyOptions|undefined,
 *  "shift+tab": hotkeyHandler|HotkeyOptions|undefined,
 *  arrowup: hotkeyHandler|HotkeyOptions|undefined,
 *  arrowdown: hotkeyHandler|HotkeyOptions|undefined,
 *  enter: hotkeyHandler|HotkeyOptions|undefined,
 *  arrowleft: hotkeyHandler|HotkeyOptions|undefined,
 *  arrowright: hotkeyHandler|HotkeyOptions|undefined,
 *  escape: hotkeyHandler|HotkeyOptions|undefined,
 *  space: hotkeyHandler|HotkeyOptions|undefined,
 * }} NavigationHotkeys
 */

/**
 * @typedef HotkeyOptions
 * @param {hotkeyHandler} callback
 * @param {Function} isAvailable
 * @param {boolean} bypassEditableProtection
 */

/**
 * Callback used to override the behaviour of a specific
 * key input.
 *
 * @callback hotkeyHandler
 * @param {Navigator} navigator
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
 * @returns {{
 *  enable: Function,
 *  disable: Function,
 * }}
 */
export function useNavigation(containerRef, options = {}) {
    const hotkeyService = useService("hotkey");
    containerRef = typeof containerRef === "string" ? useRef(containerRef) : containerRef;
    const navigator = new Navigator(containerRef, options, hotkeyService);

    useEffect(
        (container) => {
            if (container) {
                navigator._enable();
            } else if (navigator) {
                navigator._disable();
            }
        },
        () => [containerRef.el]
    );

    return {
        enable: () => navigator._enable(),
        disable: () => navigator._disable(),
    };
}
