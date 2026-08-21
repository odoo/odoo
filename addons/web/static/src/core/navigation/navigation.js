import {
    computed,
    onWillDestroy,
    shallowEqual,
    signal,
    untrack,
    useEffect,
    useListener,
    useOnChange,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { deepMerge } from "@web/core/utils/objects";
import { scrollTo } from "@web/core/utils/scrolling";
import { throttleForAnimation } from "@web/core/utils/timing";
import { browser } from "@web/core/browser/browser";
import { isVisible } from "@web/core/utils/ui";

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
            this.target = isVisible(subInput) ? subInput : el;
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
        if (
            this._navigator.activeItem !== this &&
            this._navigator._isNavigationAvailable(this.target)
        ) {
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

    /**@private*/ _hotkeyRemoves = [];
    /**@private*/ _hotkeyService = undefined;

    /**
     * Bumped by @see update to force a re-derivation when the DOM changed
     * under us. The DOM is not reactive, so a mutation cannot invalidate
     * @see _elements on its own.
     * @private
     */
    _domVersion = signal(0);

    /**@private*/ _isDestroyed = false;

    /**
     * The derivation of @see items the active item was last reconciled with.
     * @private
     * @type {Array<NavigationItem>|undefined}
     */
    _syncedItems = undefined;

    /**
     * The navigable elements, as returned by `options.getItems`. Any signal
     * that callback reads (the container ref, an `isOpen()` state, ...) is
     * tracked, so the list re-derives on its own when they change.
     *
     * Memoised on a shallow comparison: an `update()` that yields the same
     * elements in the same order does not invalidate @see _items, which is
     * what the old `didUpdate` bookkeeping did by hand.
     * @private
     */
    _elements = computed(
        () => {
            this._domVersion();
            return [...this._options.getItems()];
        },
        { equals: shallowEqual }
    );

    /**
     * Previous derivation of @see _items, kept so the next one can reuse the
     * NavigationItem of an element that is still there (and therefore keep
     * its listeners) rather than rebuild it.
     * @private
     * @type {Array<NavigationItem>}
     */
    _itemCache = [];

    /**
     * @private
     * @type {import("@odoo/owl").Computed<Array<NavigationItem>>}
     */
    _items = computed(() => {
        const staleItems = new Map(this._itemCache.map((item) => [item.el, item]));
        const items = [];
        const elements = this._elements();
        for (let index = 0; index < elements.length; index++) {
            const el = elements[index];
            let item = staleItems.get(el);
            if (item) {
                item.index = index;
                staleItems.delete(el);
            } else {
                item = new NavigationItem({
                    index,
                    el,
                    options: this._options,
                    navigator: this,
                });
            }
            items.push(item);
        }
        for (const item of staleItems.values()) {
            item._removeListeners();
        }
        this._itemCache = items;
        return items;
    });

    /**
     * Derived lazily: reading this from anywhere -- including a consumer's
     * own `onMounted` -- recomputes against the DOM as it is at that moment,
     * so there is no longer an ordering contract between the hook and its
     * consumers.
     * @type {Array<NavigationItem>}
     */
    get items() {
        // Guarded here rather than in the derivation: _destroy() must not
        // write to a signal, or it would wake the effect it is tearing down.
        return this._isDestroyed ? [] : this._items();
    }

    /**
     * @param {NavigationOptions} options
     * @param {import("@web/core/hotkeys/hotkey_service").HotkeyService} hotkeyService
     */
    constructor(options, hotkeyService) {
        this._hotkeyService = hotkeyService;

        /**@private*/
        this._options = deepMerge(
            {
                isNavigationAvailable: ({ target }) =>
                    this.contains(target) && (this.isFocused || this._options.virtualFocus),
                shouldFocusChildInput: true,
                shouldFocusFirstItem: false,
                shouldRegisterHotkeys: true,
                virtualFocus: false,
                hotkeys: {
                    ...(!options.virtualFocus
                        ? {}
                        : {
                              tab: {
                                  callback: () => this.next(),
                                  bypassEditableProtection: true,
                              },
                              "shift+tab": {
                                  callback: () => this.previous(),
                                  bypassEditableProtection: true,
                              },
                          }),
                    home: () => this.items[0]?.setActive(),
                    end: () => this.items.at(-1)?.setActive(),
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

        if (this._options.shouldRegisterHotkeys) {
            this.registerHotkeys();
        }
    }

    /**
     * Returns true if the current active item is not null and still inside the DOM
     * @type {boolean}
     */
    get hasActiveItem() {
        return Boolean(this.activeItem?.el.isConnected);
    }

    /**
     * Returns true if the focus is on any of the navigable items
     * @type {boolean}
     */
    get isFocused() {
        return this.items.some((item) => item.target.contains(document.activeElement));
    }

    next() {
        if (!this.hasActiveItem) {
            this.items[0]?.setActive();
        } else {
            this.items[(this.activeItemIndex + 1) % this.items.length]?.setActive();
        }
    }

    previous() {
        const index = this.activeItemIndex - 1;
        if (!this.hasActiveItem || index < 0) {
            this.items.at(-1)?.setActive();
        } else {
            this.items[index % this.items.length]?.setActive();
        }
    }

    /**
     * Invalidates the item list. The DOM is not reactive, so a caller that
     * mutated it (or a MutationObserver) has to say so; everything reachable
     * through a signal invalidates itself.
     *
     * The rebuild is lazy -- it happens on the next read of @see items -- but
     * the read-after-update contract is preserved: `update(); this.items`
     * always yields the current DOM.
     */
    update() {
        this._domVersion.set(untrack(this._domVersion) + 1);
        // Imperative callers (dropdown.js, the MutationObserver) expect the
        // active item to be reconciled by the time update() returns, so the
        // sync runs eagerly here rather than waiting for the effect. The
        // effect covers the signal-driven changes no one calls update() for.
        this._syncActiveItem();
    }

    /**
     * Reconciles the active item with a freshly derived item list: keep the
     * same element active if it survived, otherwise fall back to the nearest
     * index, then the focused element, then nothing.
     *
     * Focus is moved here, so this must run from an effect, never from the
     * derivation itself -- a plain read of `items` (from a render, from a
     * hotkey callback) must not steal focus.
     * @param {Array<NavigationItem>} [items] the derivation to reconcile
     *  against, when the caller already read (and tracked) it
     * @private
     */
    _syncActiveItem(items = this.items) {
        // Idempotent per derivation: whichever of update() and the effect gets
        // here first does the work, the other one is a no-op. This is what the
        // old `didUpdate` flag bought, without the ordering contract.
        if (items === this._syncedItems) {
            return;
        }
        this._syncedItems = items;

        const oldActiveItem = this.activeItem;
        const activeItemIndex =
            oldActiveItem && oldActiveItem.el.isConnected
                ? items.findIndex((item) => item.el === oldActiveItem.el)
                : -1;
        const focusedElementIndex = items.findIndex((item) => item.el === document.activeElement);
        if (activeItemIndex > -1) {
            this._updateActiveItemIndex(activeItemIndex);
        } else if (this.activeItemIndex >= 0) {
            const closest = Math.min(this.activeItemIndex, items.length - 1);
            this._updateActiveItemIndex(closest);
        } else if (focusedElementIndex >= 0) {
            this._updateActiveItemIndex(focusedElementIndex);
        } else {
            this._updateActiveItemIndex(-1);
        }

        this._options.onUpdated?.(this);

        if (this._options.shouldFocusFirstItem) {
            items[0]?.setActive();
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
        if (this._hotkeyRemoves.length > 0) {
            return;
        }

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
                        this._isNavigationAvailable(target) &&
                        isAvailable({ navigator: this, target }),
                    bypassEditableProtection,
                })
            );
        }
    }

    unregisterHotkeys() {
        for (const removeHotkey of this._hotkeyRemoves) {
            removeHotkey();
        }
        this._hotkeyRemoves = [];
    }

    /**
     * @private
     */
    _destroy() {
        this._isDestroyed = true;
        for (const item of this._itemCache) {
            item._removeListeners();
        }
        this._itemCache = [];
        this._syncedItems = undefined;
        this.unregisterHotkeys();
    }

    /**
     * @private
     */
    _setActiveItem(index) {
        this.activeItem?.setInactive(false);
        this.activeItemIndex = index;
        if (index >= 0) {
            this.activeItem = this.items[index];
            this._options.onItemActivated?.(this.activeItem.el);
        } else {
            this.activeItem = null;
        }
    }

    /**
     * @private
     */
    _updateActiveItemIndex(index) {
        if (this.items[index]) {
            const shouldFocus = !this.items.some((item) => item.target === document.activeElement);
            this.items[index].setActive(shouldFocus);
        } else {
            this.activeItemIndex = -1;
            this.activeItem = null;
        }
    }

    /**
     * @private
     */
    _isNavigationAvailable(target) {
        return this._options.isNavigationAvailable({ navigator: this, target });
    }

    /**
     * @private
     */
    _checkFocus(target) {
        if (!(target instanceof HTMLElement) || !this._isNavigationAvailable(target)) {
            this._setActiveItem(-1);
        }
    }
}

/**
 * @typedef {Object} NavigationOptions
 * @property {() => HTMLElement[]} getItems
 * @property {({{ navigator: Navigator, target: HTMLElement }}) => bool} isNavigationAvailable
 * @property {NavigationHotkeys} hotkeys
 * @property {Function} onUpdated
 * @property {Function} onItemActivated
 * @property {Boolean} [virtualFocus=false] - If true, items are only visually
 * focused so the actual focus can be kept on another input.
 * @property {Boolean} [shouldFocusChildInput=false] - If true, elements like inputs or buttons
 * inside of the items are focused instead of the items themselves.
 * @property {Boolean} [shouldRegisterHotkeys=true] - If true, registers all hotkeys directly when
 * the hook is called.
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
 * @param {import("@odoo/owl").Signal<HTMLElement>} containerRef ref on the
 *  container element (`null` while unmounted)
 * @param {NavigationOptions} options
 * @returns {Navigator}
 */
export function useNavigation(containerRef, options = {}) {
    // The optional chaining keeps this null-safe (a ref can be undefined before
    // mount), so it can never throw "Cannot read properties of undefined".
    const getContainerEl = () => containerRef?.();

    const newOptions = { ...options };
    if (!newOptions.getItems) {
        newOptions.getItems = () => getContainerEl()?.querySelectorAll(":scope .o-navigable") ?? [];
    }

    const hotkeyService = useService("hotkey");
    const navigator = new Navigator(newOptions, hotkeyService);
    const observer = new MutationObserver(() => navigator.update());

    // The item list derives itself from `getItems` -- which reads the container
    // ref -- so nothing has to push an update in here. All this has to do is
    // watch the derived list and reconcile the active item with it, which is a
    // side effect and cannot live in the derivation.
    useEffect(() => {
        // Skip the setup-time run, where the ref is still null and the list is
        // trivially empty: firing onUpdated with no items before mount is
        // noise the old useLayoutEffect never produced.
        if (!getContainerEl()) {
            return;
        }
        const items = navigator.items;
        untrack(() => navigator._syncActiveItem(items));
    });

    // The DOM is the one input that cannot invalidate the derivation on its
    // own, so it gets an observer.
    useOnChange(
        () => [getContainerEl()],
        (containerEl) => {
            if (containerEl) {
                observer.observe(containerEl, {
                    childList: true,
                    subtree: true,
                });
                return () => observer.disconnect();
            }
        }
    );

    useListener(browser, "focus", ({ target }) => navigator._checkFocus(target), true);
    onWillDestroy(() => navigator._destroy());

    return navigator;
}
