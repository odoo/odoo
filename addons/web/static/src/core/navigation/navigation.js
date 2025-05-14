import { onWillUnmount, useEffect, useRef } from "@odoo/owl";
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

    constructor({ index, el, options, navigator }) {
        this.index = index;

        /**@private */
        this._options = options;

        /**
         * @private
         * @type {Navigator}
         */
        this._navigator = navigator;

        this.el = el;
        if (this._options.shouldFocusChildInput) {
            const subInput = el.querySelector(":scope input, :scope button, :scope textarea");
            this.target = subInput || el;
        } else {
            this.target = el;
        }

        if (this.el.ariaSelected !== true) {
            this.el.ariaSelected = false;
        }

        const onFocus = () => this.setActive(false);
        const onMouseMove = () => this._onMouseMove();

        this.target.addEventListener("focus", onFocus);
        this.target.addEventListener("mousemove", onMouseMove);

        /**@private*/
        this._removeListeners = () => {
            this.target.removeEventListener("focus", onFocus);
            this.target.removeEventListener("mousemove", onMouseMove);
        };
    }

    select() {
        this.setActive();
        this.target.click();
    }

    setActive(focus = true) {
        scrollTo(this.target);
        this._navigator._setActiveItem(this.index);
        this.target.classList.add(ACTIVE_ELEMENT_CLASS);
        this.target.ariaSelected = true;

        if (focus && !this._options.virtualFocus) {
            throttledFocus.cancel();
            throttledFocus(this.target);
        }
    }

    setInactive(blur = true) {
        this.target.classList.remove(ACTIVE_ELEMENT_CLASS);
        this.target.ariaSelected = false;
        if (blur && !this._options.virtualFocus) {
            this.target.blur();
        }
    }

    /**
     * @private
     */
    _onMouseMove() {
        if (this._navigator.activeItem !== this) {
            this.setActive(false);
            this._options.onMouseEnter?.(this);
        }
    }
}

export class Navigator {
    /**@type {NavigationItem|undefined}*/
    activeItem = undefined;

    /**@type {number}*/
    activeItemIndex = -1;

    /**@type {Array<NavigationItem>}*/
    items = [];

    /**@private*/ _hotkeyRemoves = [];
    /**@private*/ _hotkeyService = undefined;

    /**
     * @param {NavigationOptions} options
     * @param {import("@web/core/hotkeys/hotkey_service").HotkeyService} hotkeyService
     */
    constructor(options, hotkeyService) {
        this._hotkeyService = hotkeyService;

        /**@private*/
        this._options = deepMerge(
            {
                isNavigationAvailable: ({ target }) => this.contains(target),
                shouldFocusChildInput: true,
                virtualFocus: false,
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
                        isAvailable: ({ navigator }) => Boolean(navigator.activeItem),
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

        for (const [hotkey, hotkeyInfo] of Object.entries(this._options.hotkeys)) {
            if (!hotkeyInfo) {
                continue;
            }

            const callback = typeof hotkeyInfo == "function" ? hotkeyInfo : hotkeyInfo.callback;
            if (!callback) {
                continue;
            }

            const isAvailable = hotkeyInfo?.isAvailable ?? (() => true);
            const bypassEditableProtection = hotkeyInfo?.bypassEditableProtection ?? false;
            const allowRepeat = hotkeyInfo?.allowRepeat ?? true;

            this._hotkeyRemoves.push(
                this._hotkeyService.add(hotkey, async () => await callback(this), {
                    global: true,
                    allowRepeat,
                    isAvailable: (target) =>
                        this._options.isNavigationAvailable({ navigator: this, target }) &&
                        isAvailable({ navigator: this, target }),
                    bypassEditableProtection,
                })
            );
        }
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

    update() {
        const oldItems = new Map(this.items.map((item) => [item.el, item]));
        const oldActiveItem = this.activeItem;
        const elements = this._options.getItems();
        this.items = [];

        for (let index = 0; index < elements.length; index++) {
            const element = elements[index];

            let item = oldItems.get(element);
            if (item) {
                item.index = index;
                oldItems.delete(element);
            } else {
                item = new NavigationItem({
                    index,
                    el: element,
                    options: this._options,
                    navigator: this,
                });
            }
            this.items.push(item);
        }

        for (const item of oldItems.values()) {
            item._removeListeners();
        }

        const activeItemIndex =
            oldActiveItem && oldActiveItem.el.isConnected
                ? this.items.findIndex((item) => item.el === oldActiveItem.el)
                : -1;
        if (activeItemIndex > -1) {
            this._updateActiveItemIndex(activeItemIndex);
        } else if (this.activeItemIndex >= 0) {
            const closest = Math.min(this.activeItemIndex, elements.length - 1);
            this._updateActiveItemIndex(closest);
        } else {
            this._updateActiveItemIndex(-1);
        }

        this._options.onUpdated?.(this);
    }

    /**
     * @param {HTMLElement} target
     * @returns {boolean}
     */
    contains(target) {
        return this.items.some((item) => item.target === target);
    }

    /**
     * @private
     */
    _destroy() {
        for (const item of this.items) {
            item._removeListeners();
        }
        this.items = [];

        for (const removeHotkey of this._hotkeyRemoves) {
            removeHotkey();
        }
        this._hotkeyRemoves = [];
    }

    /**
     * @private
     */
    _setActiveItem(index) {
        this.activeItem?.setInactive(false);
        this.activeItem = this.items[index];
        this.activeItemIndex = index;
    }

    /**
     * @private
     */
    _updateActiveItemIndex(index) {
        if (this.items[index]) {
            this.items[index].setActive();
        } else {
            this.activeItemIndex = -1;
            this.activeItem = null;
        }
    }
}

/**
 * @typedef {Object} NavigationOptions
 * @property {() => HTMLElement[]} getItems
 * @property {({{ navigator: Navigator, target: HTMLElement }}) => bool} isNavigationAvailable
 * @property {NavigationHotkeys} hotkeys
 * @property {Function} onUpdated
 * @property {Boolean} [virtualFocus=false] - If true, items are only visually
 * focused so the actual focus can be kept on another input.
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
 * @param {({{ navigator: Navigator, target: HTMLElement }}) => bool} isAvailable
 * @param {boolean} bypassEditableProtection
 * @param {boolean} [allowRepeat=true]
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
 * @returns {Navigator}
 */
export function useNavigation(containerRef, options = {}) {
    containerRef = typeof containerRef === "string" ? useRef(containerRef) : containerRef;

    const newOptions = { ...options };
    if (!newOptions.getItems) {
        newOptions.getItems = () => containerRef.el?.querySelectorAll(":scope .o-navigable") ?? [];
    }

    const hotkeyService = useService("hotkey");
    const navigator = new Navigator(newOptions, hotkeyService);
    const observer = new MutationObserver(() => navigator.update());

    useEffect(
        (containerEl) => {
            if (containerEl) {
                navigator.update();
                observer.observe(containerEl, {
                    childList: true,
                    subtree: true,
                });
            }
            return () => observer.disconnect();
        },
        () => [containerRef.el]
    );

    onWillUnmount(() => navigator._destroy());

    return navigator;
}
