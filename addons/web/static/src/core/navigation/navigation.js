import { useEffect, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { scrollTo } from "@web/core/utils/scrolling";
import { throttleForAnimation } from "@web/core/utils/timing";

export const ACTIVE_ELEMENT_CLASS = "focus";
const throttledFocus = throttleForAnimation((el) => el?.focus());

export class NavigationItem {
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
        this.options = options;

        /**@private*/
        this._setActiveItem = setActiveItem;

        this.el = el;
        if (this.options.shouldFocusChildInput) {
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

        if (focus && !this.options.virtualFocus) {
            throttledFocus.cancel();
            throttledFocus(this.target);
        }
    }

    /**
     * @private
     */
    _onMouseEnter() {
        this.setActive(false);
        this.options.onMouseEnter?.(this);
    }
}

export class Navigator {
    enabled = false;

    /**@type {Array<NavigationItem>} */
    items = [];

    /**@type {NavigationItem|undefined}*/
    activeItem = undefined;

    /**@type {number}*/
    activeItemIndex = -1;

    /**@private */
    _targetObserver = undefined;
    /**@private */
    _initialFocusElement = undefined;

    /**@private */
    _hotkeyRemoves = [];
    /**@private */
    _hotkeyService = undefined;

    /**
     * @param {*} containerRef
     * @param {NavigationOptions} options
     */
    constructor(containerRef, options, hotkeyService) {
        this.containerRef = containerRef;
        this._hotkeyService = hotkeyService;

        this.options = {
            shouldFocusChildInput: true,
            virtualFocus: false,
            itemsSelector: ":scope .o-navigable",
            focusInitialElementOnDisabled: () => true,
            ...options,

            allowedInEditableHotkeys: [
                "arrowup",
                "arrowdown",
                "enter",
                "tab",
                "shift+tab",
                ...(options?.allowedInEditableHotkeys || []),
            ],

            hotkeys: {
                home: ({ event }) => {
                    event.preventDefault();
                    this.items[0]?.setActive();
                },
                end: ({ event }) => {
                    event.preventDefault();
                    this.items.at(-1)?.setActive();
                },
                tab: ({ event }) => {
                    event.preventDefault();
                    this.next();
                },
                "shift+tab": ({ event }) => {
                    event.preventDefault();
                    this.previous();
                },
                arrowdown: ({ event }) => {
                    event.preventDefault();
                    this.next();
                },
                arrowup: ({ event }) => {
                    event.preventDefault();
                    this.previous();
                },
                enter: ({ event }) => {
                    event.preventDefault();
                    const item = this.activeItem || this.items[0];
                    item?.select();
                },
                ...(options?.hotkeys || {}),
            },
        };
    }

    /**
     * Returns true if the focus is on any of the navigable items
     * @type {boolean}
     */
    get isFocused() {
        return Boolean(this.activeItem?.el.isConnected);
    }

    enable() {
        if (!this.containerRef.el || this._targetObserver) {
            return;
        }

        for (const [hotkey, callback] of Object.entries(this.options.hotkeys)) {
            if (!callback) {
                continue;
            }

            this._hotkeyRemoves.push(
                this._hotkeyService.add(
                    hotkey,
                    ({ event }) => callback({ navigator: this, event }),
                    {
                        allowRepeat: true,
                        preventDefault: false,
                        bypassEditableProtection:
                            this.options.allowedInEditableHotkeys.includes(hotkey),
                    }
                )
            );
        }

        this._targetObserver = new MutationObserver(() => this.update());
        this._targetObserver.observe(this.containerRef.el, {
            childList: true,
            subtree: true,
        });

        this._initialFocusElement = document.activeElement;
        this.activeItemIndex = -1;
        this.update();

        if (this.options.onEnabled) {
            this.options.onEnabled(this.items);
        } else if (this.items.length > 0) {
            this.items[0]?.setActive();
        }

        this.enabled = true;
    }

    disable() {
        if (!this.enabled) {
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

        if (this.options.focusInitialElementOnDisabled()) {
            throttledFocus.cancel();
            throttledFocus(this._initialFocusElement);
        }

        this.enabled = false;
    }

    update() {
        if (!this.containerRef.el) {
            return;
        }
        const oldActiveItem = this.activeItem;
        const oldItemsLength = this.items.length;

        const elements = [...this.containerRef.el.querySelectorAll(this.options.itemsSelector)];
        if (this.items.length > elements.length) {
            this.items.splice(elements.length - this.items.length);
        }

        for (let i = 0; i < elements.length; i++) {
            const navItem = new NavigationItem({
                index: i,
                el: elements[i],
                options: this.options,
                setActiveItem: (index) => this.setActiveItem(index),
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

    setActiveItem(index) {
        if (this.activeItem) {
            this.activeItem.el.classList.remove(ACTIVE_ELEMENT_CLASS);
        }
        this.activeItem = this.items[index];
        this.activeItemIndex = index;
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
 * @param {NavigationData} data
 */

/**
 * @typedef NavigationData
 * @property {KeyboardEvent} event
 * @property {Navigator} navigator
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

    return navigator;
}
