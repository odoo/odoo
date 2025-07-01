import { onMounted, onWillDestroy, useEffect, useRef } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { deepMerge } from "@web/core/utils/objects";
import { scrollTo } from "@web/core/utils/scrolling";
import { throttleForAnimation } from "@web/core/utils/timing";

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
 * @property {string} activeClass - CSS class which is added on the currently
 * active element.
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
 * @param {boolean} [preventDefault=true]
 * @param {boolean} [allowRepeat=true]
 */

/**
 * Callback used to override the behaviour of a specific
 * key input.
 *
 * @callback hotkeyHandler
 * @param {Navigator} navigator
 */

export const ACTIVE_ELEMENT_CLASS = "focus";

const DISPATCH_RESULTS = {
    Failed: -1,
    PreventDefault: 0,
    DontPrevent: 1,
};

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
        this.target.ariaSelected = true;
        this.target.classList.add(this._options.activeClass);

        if (focus && !this._options.virtualFocus) {
            throttledFocus.cancel();
            throttledFocus(this.target);
        }
    }

    setInactive(blur = true) {
        this.target.classList.remove(this._options.activeClass);
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

    /**@private*/
    _options = {};

    /**
     * @param {NavigationOptions} options
     */
    constructor(options) {
        this._options = deepMerge(
            {
                isNavigationAvailable: ({ target }) => this.contains(target),
                shouldFocusChildInput: true,
                virtualFocus: false,
                activeClass: ACTIVE_ELEMENT_CLASS,
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
     * @param {KeyboardEvent} event
     * @returns {number}
     */
    async _dispatch(event) {
        const hotkey = getActiveHotkey(event);

        const data = { navigator: this, target: event.target };
        if (this._options.isNavigationAvailable(data)) {
            const hotkeyInfo = this._options.hotkeys[hotkey];

            if (typeof hotkeyInfo === "function") {
                await hotkeyInfo(this, event);
                return DISPATCH_RESULTS.PreventDefault;
            }

            if (
                !hotkeyInfo ||
                !hotkeyInfo.callback ||
                ("isAvailable" in hotkeyInfo && !hotkeyInfo.isAvailable(data)) ||
                (event.repeat && hotkeyInfo.allowRepeat === false)
            ) {
                return DISPATCH_RESULTS.Failed;
            }

            const targetIsEditable =
                event.target instanceof HTMLElement &&
                (/input|textarea/i.test(event.target.tagName) || event.target.isContentEditable) &&
                !event.target.matches("input[type=checkbox], input[type=radio]");
            if (targetIsEditable && !hotkeyInfo.bypassEditableProtection && hotkey !== "escape") {
                return DISPATCH_RESULTS.Failed;
            }

            await hotkeyInfo.callback(this, event);
            return hotkeyInfo.preventDefault === false
                ? DISPATCH_RESULTS.DontPrevent
                : DISPATCH_RESULTS.PreventDefault;
        }

        return DISPATCH_RESULTS.Failed;
    }

    /**
     * @private
     */
    _destroy() {
        for (const item of this.items) {
            item._removeListeners();
        }
        this.items = [];
    }

    /**
     * @private
     */
    _setActiveItem(index) {
        this.activeItem?.setInactive(false);
        this.activeItem = this.items[index];
        this.activeItemIndex = index;
        this._options.onNavigated?.(this);
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

export const navigationService = {
    dependencies: ["ui"],
    start(env, { ui }) {
        const navigators = [];

        browser.addEventListener(
            "keydown",
            async (event) => {
                for (let i = navigators.length - 1; i >= 0; i--) {
                    const dispatchResult = await navigators[i]._dispatch(event);
                    if (dispatchResult !== DISPATCH_RESULTS.Failed) {
                        if (dispatchResult === DISPATCH_RESULTS.PreventDefault) {
                            event.preventDefault();
                            event.stopImmediatePropagation();
                        }
                        return;
                    }
                }
            },
            true
        );

        return {
            registerNavigator: (navigator) => {
                navigators.push(navigator);
            },
            unregisterNavigator: (navigator) => {
                const i = navigators.indexOf(navigator);
                if (i >= 0) {
                    navigators.splice(i, 1);
                }
            },
        };
    },
};

registry.category("services").add("navigation", navigationService);

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

    const navigationService = useService("navigation");
    const navigator = new Navigator(newOptions);
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

    onMounted(() => {
        navigationService.registerNavigator(navigator);
        navigator.update();
    });

    onWillDestroy(() => {
        navigator._destroy();
        navigationService.unregisterNavigator(navigator);
    });

    return navigator;
}
