// @ts-check
/** @odoo-module native */

import { onWillDestroy, reactive, useEffect, useRef } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { deepMerge } from "@web/core/utils/collections/objects";
import { scrollTo } from "@web/core/utils/dom/scrolling";
import { getActiveElement } from "@web/core/utils/dom/ui";
import { useService } from "@web/core/utils/hooks";
import { throttleForAnimation } from "@web/core/utils/timing";
export const ACTIVE_ELEMENT_CLASS = "focus";

const ARIA_SELECTED_ROLES = new Set([
    "columnheader",
    "gridcell",
    "option",
    "row",
    "rowheader",
    "tab",
    "treeitem",
]);

const ARIA_ACTIVEDESCENDANT_ROLES = new Set([
    "application",
    "combobox",
    "grid",
    "group",
    "listbox",
    "menu",
    "menubar",
    "radiogroup",
    "row",
    "searchbox",
    "spinbutton",
    "tablist",
    "textbox",
    "toolbar",
    "tree",
    "treegrid",
]);

/**
 * @param {HTMLElement} el
 * @returns {boolean}
 */
function supportsAriaSelected(el) {
    return ARIA_SELECTED_ROLES.has(el.getAttribute("role") ?? "");
}

let navigationItemId = 0;

class NavigationItem {
    /** @type {number} */
    index = -1;

    /** @type {HTMLElement} */
    el;

    /** @type {HTMLElement} */
    target;

    /** @param {{ index: number, el: HTMLElement, options: NavigationOptions, navigator: Navigator }} param0 */
    constructor({ index, el, options, navigator }) {
        this.index = index;

        /** @private */
        this._options = options;

        /**
         * @private
         * @type {Navigator}
         */
        this._navigator = navigator;

        this.el = el;
        if (this._options.shouldFocusChildInput) {
            const subInput = el.querySelector(
                ":scope input, :scope button, :scope textarea",
            );
            this.target = /** @type {HTMLElement} */ (subInput || el);
        } else {
            this.target = el;
        }

        /** @private */
        this._ownsAriaSelected =
            supportsAriaSelected(this.el) && !this.el.hasAttribute("aria-selected");
        if (this._ownsAriaSelected) {
            this.el.ariaSelected = "false";
        }

        const onFocus = () => this.setActive(false);
        this.target.addEventListener("focus", onFocus);

        if (this._options.mouseActivation === "armed") {
            const hoverTarget = this._options.getHoverTarget?.(el) ?? this.target;
            const onMouseEnter = () => this._onArmedMouseEnter();
            const onMouseLeave = () => this._onArmedMouseLeave();
            hoverTarget.addEventListener("mouseenter", onMouseEnter);
            hoverTarget.addEventListener("mouseleave", onMouseLeave);
            this._removeListeners = () => {
                this.target.removeEventListener("focus", onFocus);
                hoverTarget.removeEventListener("mouseenter", onMouseEnter);
                hoverTarget.removeEventListener("mouseleave", onMouseLeave);
            };
        } else {
            const onMouseMove = () => this._onMouseMove();
            this.target.addEventListener("mousemove", onMouseMove);
            this._removeListeners = () => {
                this.target.removeEventListener("focus", onFocus);
                this.target.removeEventListener("mousemove", onMouseMove);
            };
        }
    }

    select() {
        this.setActive();
        this.target.click();
    }

    setActive(focus = true) {
        if (focus) {
            (this._options.scrollTo ?? scrollTo)(this.target);
        }
        this._navigator._setActiveItem(this.index);
        this.target.classList.add(this._options.activeClass ?? ACTIVE_ELEMENT_CLASS);
        this._setAriaSelected("true");

        if (focus && !this._options.virtualFocus) {
            this._navigator._throttledFocus.cancel();
            this._navigator._throttledFocus(this.target);
        }
    }

    setInactive(blur = true) {
        this.target.classList.remove(this._options.activeClass ?? ACTIVE_ELEMENT_CLASS);
        this._setAriaSelected("false");
        if (blur && !this._options.virtualFocus) {
            this.target.blur();
        }
    }

    /**
     * @private
     * @param {"true" | "false"} value
     */
    _setAriaSelected(value) {
        if (this._ownsAriaSelected) {
            this.el.ariaSelected = value;
        }
    }

    /** @private */
    _onMouseMove() {
        if (
            this._navigator.activeItem !== this &&
            this._navigator._isNavigationAvailable(this.target)
        ) {
            this.setActive(false);
            this._options.onMouseEnter?.(this);
        }
    }

    /** @private */
    _onArmedMouseEnter() {
        if (
            this._navigator.isMouseArmed &&
            this._navigator.activeItem !== this &&
            this._navigator._isNavigationAvailable(this.target)
        ) {
            this.setActive(false);
            this._options.onMouseEnter?.(this);
        }
    }

    /** @private */
    _onArmedMouseLeave() {
        if (this._navigator.isMouseArmed) {
            this._navigator.clearActiveItem();
        }
    }
}

export class Navigator {
    /** @type {Array<NavigationItem>} */
    items = [];

    /**
     * Bound by `useNavigation`: points the navigator's mutation observer at
     * a container, or at nothing. A bare Navigator watches no DOM.
     *
     * @type {(containerEl: HTMLElement | null) => void}
     */
    observe = () => {};

    /** @private @type {Array<() => void>} */ _hotkeyRemoves = [];
    /** @private @type {import("@web/core/hotkeys/hotkey_service").HotkeyService} */ _hotkeyService;

    /**
     * @param {NavigationOptions} options
     * @param {import("@web/core/hotkeys/hotkey_service").HotkeyService} hotkeyService
     */
    constructor(options, hotkeyService) {
        this._hotkeyService = hotkeyService;
        this._throttledFocus = throttleForAnimation((/** @type {HTMLElement} */ el) =>
            el?.focus(),
        );
        this.state = reactive({
            /** @type {number} */
            activeItemIndex: -1,
            /** @type {HTMLElement | null} */
            activeItemEl: null,
            itemsRevision: 0,
        });

        /** @private */
        this._options = mergeNavigationOptions(this._makeDefaultOptions(), options);

        /**
         * @private
         * @type {boolean}
         */
        this._mouseArmed = false;
        /**
         * @private
         * @type {(() => void) | null}
         */
        this._disarmMouse = null;
        this._rearmMouse();

        if (this._options.shouldRegisterHotkeys) {
            this.registerHotkeys();
        }
    }

    /**
     * @private
     * @returns {NavigationOptions}
     */
    _makeDefaultOptions() {
        return {
            isNavigationAvailable: (
                /** @type {{ navigator: Navigator, target: HTMLElement }} */ { target },
            ) => {
                if (this.contains(target)) {
                    return Boolean(this.isFocused || this._options.virtualFocus);
                }
                return Boolean(
                    this._options.virtualFocus &&
                    this._options.getContainer?.()?.contains(target),
                );
            },
            activeClass: ACTIVE_ELEMENT_CLASS,
            mouseActivation: "movement",
            shouldFocusChildInput: true,
            shouldFocusFirstItem: false,
            shouldRegisterHotkeys: true,
            virtualFocus: false,
            wrap: true,
            hotkeys: {
                home: () => this.activateFirst(),
                end: () => this.activateLast(),
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
                    isAvailable: (
                        /** @type {{ navigator: Navigator, target: HTMLElement }} */ {
                            navigator,
                        },
                    ) => Boolean(navigator.activeItem),
                    callback: () => {
                        const item = this.activeItem || this.items[0];
                        item?.select();
                    },
                    bypassEditableProtection: true,
                },
            },
        };
    }

    /** @type {number} */
    get activeItemIndex() {
        return this.state.activeItemIndex;
    }
    set activeItemIndex(value) {
        this.state.activeItemIndex = value;
    }

    /** @type {NavigationItem | null} */
    get activeItem() {
        const idx = this.state.activeItemIndex;
        return idx >= 0 ? (this.items[idx] ?? null) : null;
    }

    /** @type {boolean} */
    get hasActiveItem() {
        return Boolean(this.activeItem?.el.isConnected);
    }

    /** @type {boolean} */
    get isFocused() {
        const active = this._activeElement();
        return (
            Boolean(active) && this.items.some((item) => item.target.contains(active))
        );
    }

    /**
     * @private
     * @returns {Element | null}
     */
    _activeElement() {
        return getActiveElement(
            this._options.getContainer?.() ?? this.items[0]?.target ?? document,
        );
    }

    /** @type {boolean} */
    get isMouseArmed() {
        return this._mouseArmed;
    }

    next() {
        this._rearmMouse();
        if (!this.hasActiveItem) {
            this.items[0]?.setActive();
        } else if (
            this.activeItemIndex + 1 >= this.items.length &&
            !this._options.wrap
        ) {
            this.clearActiveItem();
        } else {
            this.items[(this.activeItemIndex + 1) % this.items.length]?.setActive();
        }
    }

    previous() {
        this._rearmMouse();
        const hasActive = this.hasActiveItem;
        const index = this.activeItemIndex - 1;
        if (!hasActive) {
            this.items.at(-1)?.setActive();
        } else if (index < 0) {
            if (this._options.wrap) {
                this.items.at(-1)?.setActive();
            } else {
                this.clearActiveItem();
            }
        } else {
            this.items[index]?.setActive();
        }
    }

    activateFirst() {
        this._rearmMouse();
        if (this.items.length) {
            this.items[0].setActive();
        } else {
            this.clearActiveItem();
        }
    }

    activateLast() {
        this._rearmMouse();
        if (this.items.length) {
            this.items.at(-1)?.setActive();
        } else {
            this.clearActiveItem();
        }
    }

    clearActiveItem() {
        this._setActiveItem(-1);
    }

    update() {
        const oldItems = new Map(this.items.map((item) => [item.el, item]));
        const oldActiveItem = this.activeItem;
        const activeElement = this._activeElement();
        const focusWasInMenu =
            this.isFocused ||
            !activeElement ||
            activeElement === activeElement.ownerDocument.body;
        const elements = this._options.getItems();
        this.items = [];

        let didUpdate = elements.length !== oldItems.size;
        for (let index = 0; index < elements.length; index++) {
            const element = elements[index];

            let item = oldItems.get(element);
            if (item) {
                if (item.index !== index) {
                    item.index = index;
                    didUpdate = true;
                }
                oldItems.delete(element);
            } else {
                didUpdate = true;
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

        if (didUpdate) {
            const activeItemIndex = oldActiveItem?.el.isConnected
                ? this.items.findIndex((item) => item.el === oldActiveItem.el)
                : -1;
            const focusedElementIndex = this.items.findIndex(
                (item) => item.el === activeElement,
            );
            if (activeItemIndex > -1) {
                this._updateActiveItemIndex(activeItemIndex, focusWasInMenu);
            } else if (this.activeItemIndex >= 0) {
                const closest = Math.min(this.activeItemIndex, elements.length - 1);
                this._updateActiveItemIndex(closest, focusWasInMenu);
            } else if (focusedElementIndex >= 0) {
                this._updateActiveItemIndex(focusedElementIndex, true);
            } else {
                this._updateActiveItemIndex(-1, focusWasInMenu);
            }

            this._options.onUpdated?.(this);

            if (this._options.shouldFocusFirstItem) {
                this.items[0]?.setActive();
            }
            this.state.itemsRevision++;
        }
    }

    /**
     * @param {HTMLElement} target
     * @returns {boolean}
     */
    contains(target) {
        return this.items.some((item) => item.target.contains(target));
    }

    registerHotkeys() {
        if (this._hotkeyRemoves.length) {
            return;
        }

        for (const [hotkey, hotkeyInfo] of Object.entries(this._options.hotkeys)) {
            if (!hotkeyInfo) {
                continue;
            }

            const callback =
                typeof hotkeyInfo == "function" ? hotkeyInfo : hotkeyInfo.callback;
            if (!callback) {
                continue;
            }

            const isAvailable = hotkeyInfo?.isAvailable ?? (() => true);
            const bypassEditableProtection =
                hotkeyInfo?.bypassEditableProtection ?? false;
            const allowRepeat = hotkeyInfo?.allowRepeat ?? true;

            this._hotkeyRemoves.push(
                this._hotkeyService.add(hotkey, async () => await callback(this), {
                    global: true,
                    allowRepeat,
                    isAvailable: (/** @type {HTMLElement} */ target) =>
                        this._isNavigationAvailable(target) &&
                        isAvailable({ navigator: this, target }),
                    bypassEditableProtection,
                }),
            );
        }
    }

    unregisterHotkeys() {
        for (const removeHotkey of this._hotkeyRemoves) {
            removeHotkey();
        }
        this._hotkeyRemoves = [];
    }

    /** @private */
    _rearmMouse() {
        if (this._options.mouseActivation !== "armed") {
            return;
        }
        this._mouseArmed = false;
        this._disarmMouse?.();
        const arm = () => {
            this._mouseArmed = true;
            this._disarmMouse = null;
        };
        browser.addEventListener("mousemove", arm, { capture: true, once: true });
        this._disarmMouse = () =>
            browser.removeEventListener("mousemove", arm, { capture: true });
    }

    _destroy() {
        this._throttledFocus.cancel();
        this._disarmMouse?.();
        this._disarmMouse = null;
        this._mouseArmed = false;
        for (const item of this.items) {
            item._removeListeners();
        }
        this.items = [];
        this.state.activeItemIndex = -1;
        this.state.activeItemEl = null;
        this.state.itemsRevision++;
        this._syncActiveDescendant();
        this.unregisterHotkeys();
    }

    /**
     * @private
     * @returns {HTMLElement | null}
     */
    _getAriaOwner() {
        const container = this._options.getContainer?.() ?? null;
        const hasCompositeRole = (/** @type {Element | null} */ el) =>
            Boolean(el) &&
            ARIA_ACTIVEDESCENDANT_ROLES.has(el.getAttribute("role") ?? "");
        if (this._options.virtualFocus) {
            const focused = /** @type {HTMLElement | null} */ (
                getActiveElement(container)
            );
            if (focused && focused !== container && hasCompositeRole(focused)) {
                return focused;
            }
        }
        return hasCompositeRole(container) ? container : null;
    }

    /** @private */
    _syncActiveDescendant() {
        const owner = this._getAriaOwner();
        if (this._ariaOwner && this._ariaOwner !== owner) {
            this._ariaOwner.removeAttribute("aria-activedescendant");
        }
        this._ariaOwner = owner;
        if (!owner) {
            return;
        }
        const activeEl = this.state.activeItemEl;
        if (!activeEl) {
            owner.removeAttribute("aria-activedescendant");
            return;
        }
        if (!activeEl.id) {
            activeEl.id = `o-navigation-item-${++navigationItemId}`;
        }
        owner.setAttribute("aria-activedescendant", activeEl.id);
    }

    /** @param {number} index */
    _setActiveItem(index) {
        this.activeItem?.setInactive(false);
        const item = index >= 0 ? this.items[index] : undefined;
        this.state.activeItemEl = item?.el ?? null;
        this.state.activeItemIndex = item ? index : -1;
        this._syncActiveDescendant();
        if (item) {
            this._options.onItemActivated?.(item.el);
        }
    }

    /**
     * @private
     * @param {number} index
     * @param {boolean} [mayFocus=true]
     */
    _updateActiveItemIndex(index, mayFocus = true) {
        if (this.items[index]) {
            const active = mayFocus ? this._activeElement() : null;
            const shouldFocus =
                mayFocus && !this.items.some((item) => item.target === active);
            this.items[index].setActive(shouldFocus);
        } else {
            this._setActiveItem(-1);
        }
    }

    /** @param {HTMLElement} target */
    _isNavigationAvailable(target) {
        return this._options.isNavigationAvailable({ navigator: this, target });
    }

    /** @param {EventTarget | null} target */
    _checkFocus(target) {
        const isEl = target instanceof HTMLElement;
        const navOK = isEl && this._isNavigationAvailable(target);
        if (!isEl || !navOK) {
            this._setActiveItem(-1);
        }
    }
}

/**
 * @typedef {Object} NavigationOptions
 * @property {() => HTMLElement[]} [getItems]
 * @property {() => HTMLElement | null} [getContainer]
 * @property {(info: { navigator: Navigator, target: HTMLElement }) => boolean} [isNavigationAvailable]
 * @property {Record<string, any>} [hotkeys]
 * @property {Function} [onUpdated]
 * @property {Function} [onItemActivated]
 * @property {Function} [onMouseEnter]
 * @property {string} [activeClass]
 * @property {"movement" | "armed"} [mouseActivation]
 * @property {(el: HTMLElement) => HTMLElement} [getHoverTarget]
 * @property {(el: HTMLElement) => void} [scrollTo]
 * @property {boolean} [virtualFocus]
 * @property {boolean} [shouldFocusChildInput]
 * @property {boolean} [shouldFocusFirstItem]
 * @property {boolean} [shouldRegisterHotkeys]
 * @property {boolean} [wrap]
 */

/**
 * @typedef {Object} HotkeyOptions
 * @property {hotkeyHandler} callback
 * @property {(info: { navigator: Navigator, target: HTMLElement }) => boolean} [isAvailable]
 * @property {boolean} [bypassEditableProtection]
 * @property {boolean} [allowRepeat]
 */

/**
 * @callback hotkeyHandler
 * @param {Navigator} navigator
 */

/**
 * @param {...(NavigationOptions | undefined)} sources
 * @returns {NavigationOptions}
 */
export function mergeNavigationOptions(...sources) {
    const present = sources.filter(Boolean);
    const merged = present.reduce(
        (acc, source) => deepMerge(acc, source),
        /** @type {any} */ ({}),
    );
    /** @type {Map<PropertyKey, PropertyDescriptor>} */
    const lastDeclaration = new Map();
    for (const source of present) {
        for (const key of Reflect.ownKeys(source)) {
            const descriptor = Object.getOwnPropertyDescriptor(source, key);
            if (descriptor?.enumerable) {
                lastDeclaration.set(key, descriptor);
            }
        }
    }
    for (const [key, descriptor] of lastDeclaration) {
        if (descriptor.get) {
            Object.defineProperty(merged, key, descriptor);
        }
    }
    return merged;
}

/**
 * @param {Object} options
 * @param {string} key
 * @param {any} value
 */
function defineOption(options, key, value) {
    Object.defineProperty(options, key, {
        value,
        writable: true,
        enumerable: true,
        configurable: true,
    });
}

/**
 * @param {string|Object} containerRef
 * @param {NavigationOptions} options
 * @returns {Navigator}
 */
export function useNavigation(containerRef, options = {}) {
    containerRef =
        typeof containerRef === "string" ? useRef(containerRef) : containerRef;

    const newOptions = mergeNavigationOptions(options);
    if (!newOptions.getItems) {
        defineOption(
            newOptions,
            "getItems",
            () =>
                /** @type {any} */ (containerRef).el?.querySelectorAll(
                    ":scope .o-navigable",
                ) ?? [],
        );
    }
    if (!newOptions.getContainer) {
        defineOption(
            newOptions,
            "getContainer",
            () => /** @type {any} */ (containerRef).el ?? null,
        );
    }

    const hotkeyService = useService("hotkey");
    const navigator = new Navigator(newOptions, hotkeyService);
    const observer = new MutationObserver(() => navigator.update());

    const onFocus = (/** @type {FocusEvent} */ { target }) =>
        navigator._checkFocus(/** @type {any} */ (target));
    /** @type {HTMLElement | null} */
    let observedEl = null;
    /**
     * Watches one container at a time: the effect below hands it the ref's
     * element, and a component whose items live outside its own render
     * (a dropdown menu in an overlay) hands it that element when it opens
     * and null when it closes. Same element twice is a no-op, so the two
     * routes never stack a second observer on one menu.
     *
     * @param {HTMLElement | null} containerEl
     */
    navigator.observe = (containerEl) => {
        if (containerEl === observedEl) {
            return;
        }
        observer.disconnect();
        browser.removeEventListener("focus", onFocus, true);
        observedEl = containerEl;
        if (containerEl) {
            navigator.update();
            observer.observe(containerEl, { childList: true, subtree: true });
            browser.addEventListener("focus", onFocus, true);
        }
    };
    useEffect(
        (containerEl) => navigator.observe(containerEl),
        () => [/** @type {any} */ (containerRef).el],
    );
    onWillDestroy(() => {
        navigator.observe(null);
        navigator._destroy();
    });

    return navigator;
}
