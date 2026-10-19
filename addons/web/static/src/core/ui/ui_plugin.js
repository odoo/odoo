import { useLayoutEffect } from "@web/owl2/utils";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { BlockUI } from "./block_ui";
import { isFocusable } from "@web/core/utils/ui";
import { getActiveHotkey } from "../hotkeys/hotkey_utils";
import { getFirstAndLastTabableElements, refreshMedias, utils } from "./ui_utils";

import { computed, EventBus, Plugin, signal, untrack, useListener, usePlugin } from "@odoo/owl";

/**
 * This hook will set the UI active element
 * when the caller component will mount/patch and
 * only if the t-reffed element has some tabable elements
 * or is itself focusable.
 *
 * The caller component could pass a `t-ref` value of its template
 * to delegate the UI active element to another element than itself.
 *
 * @param {import("@web/core/utils/hooks").Ref} ref
 */
export function useActiveElement(ref) {
    if (!ref) {
        throw new Error("ref not given to useActiveElement");
    }
    const uiService = usePlugin(UIPlugin);

    function trapFocus(e) {
        const hotkey = getActiveHotkey(e);
        if (!["tab", "shift+tab"].includes(hotkey)) {
            return;
        }
        const el = e.currentTarget;
        const [firstTabableEl, lastTabableEl] = getFirstAndLastTabableElements(el);
        if (!firstTabableEl && !lastTabableEl) {
            e.preventDefault();
            e.stopPropagation();
            return;
        }
        switch (hotkey) {
            case "tab":
                if (document.activeElement === lastTabableEl) {
                    firstTabableEl.focus();
                    e.preventDefault();
                    e.stopPropagation();
                }
                break;
            case "shift+tab":
                if (document.activeElement === firstTabableEl) {
                    lastTabableEl.focus();
                    e.preventDefault();
                    e.stopPropagation();
                }
                break;
        }
    }

    useLayoutEffect(
        (el) => {
            if (el) {
                const [firstTabableEl] = getFirstAndLastTabableElements(el);
                if (!firstTabableEl && !isFocusable(el)) {
                    // no tabable elements: no need to trap focus nor become the UI active element
                    return;
                }
                const oldActiveElement = document.activeElement;
                uiService.activateElement(el);

                el.addEventListener("keydown", trapFocus);

                if (firstTabableEl) {
                    if (!el.contains(document.activeElement)) {
                        firstTabableEl.focus();
                    }
                } else if (el !== document.activeElement) {
                    el.focus();
                }
                return async () => {
                    // Components are destroyed from top to bottom, meaning that this cleanup is
                    // called before the ones of children. As a consequence, event handlers added on
                    // the current active element in children aren't removed yet, and can thus be
                    // executed if we deactivate that active element right away (e.g. the blur and
                    // change events could be triggered). For that reason, we wait for a micro-tick.
                    await Promise.resolve();
                    uiService.deactivateElement(el);
                    el.removeEventListener("keydown", trapFocus);

                    /**
                     * In some cases, the current active element is not
                     * anymore in el (e.g. with ConfirmationDialog, the
                     * confirm button is disabled when clicked, so the
                     * focus is lost). In that case, we also want to restore
                     * the focus to the previous active element so we
                     * check if the current active element is the body
                     */
                    if (
                        el.contains(document.activeElement) ||
                        document.activeElement === document.body
                    ) {
                        oldActiveElement.focus();
                    }
                };
            }
        },
        () => [untrack(ref)]
    );
}

export class UIPlugin extends Plugin {
    /** @private */
    activeElems = signal.Array([document]);
    /** @private */
    blockCount = signal(0);
    bus = new EventBus();
    // `isSmall`/`size` can't be computed here: field initializers run in the
    // constructor, before `setup()` below has a chance to (re)populate the
    // media query list, so `utils.isSmall()`/`utils.getSize()` would see an
    // empty (or stale) list and produce a wrong value that then never
    // self-corrects (a `matchMedia` "change" event only fires on a
    // transition, so if the query already matches on load, nothing fixes it).
    // They're set to their real value at the top of `setup()` instead.
    isSmall = signal(false);
    size = signal(-1);

    activeElement = computed(() => this.activeElems()[this.activeElems().length - 1]);
    isBlocked = computed(() => this.blockCount() > 0);

    setup() {
        const medias = refreshMedias();
        this.size.set(utils.getSize());
        this.isSmall.set(utils.isSmall(this));

        // block/unblock code
        registry
            .category("main_components")
            .add("BlockUI", { Component: BlockUI, props: { bus: this.bus } });

        const pointerQuery = window.matchMedia("(pointer: coarse)");
        useListener(pointerQuery, "change", (event) => {
            if (event.matches) {
                document.body.classList.add("o_touch_device");
            } else {
                document.body.classList.remove("o_touch_device");
            }
        });

        // listen to media query status changes
        const updateSizeHandler = (ev) => {
            if (ev.matches) {
                this.size.set(medias.indexOf(ev.target));
                this.isSmall.set(utils.isSmall(this));
                this.bus.trigger("resize");
            }
        };
        medias.forEach((m) => {
            if (m.addEventListener) {
                useListener(m, "change", updateSizeHandler);
            }
        });
    }

    block(data) {
        this.blockCount.set(this.blockCount() + 1);
        // TODO could probably be improved to handle multiple block demands
        // but that have different messages and delays
        if (this.blockCount() === 1) {
            this.bus.trigger("BLOCK", {
                message: data?.message,
                delay: data?.delay,
            });
        }
    }

    unblock() {
        this.blockCount.set(this.blockCount() - 1);
        if (this.blockCount() < 0) {
            console.warn(
                "Unblock ui was called more times than block, you should only unblock the UI if you have previously blocked it."
            );
            this.blockCount.set(0);
        }
        if (this.blockCount() === 0) {
            this.bus.trigger("UNBLOCK");
        }
    }

    // UI active element code

    activateElement(el) {
        this.activeElems().push(el);
        this.bus.trigger("active-element-changed", el);
    }

    deactivateElement(el) {
        this.activeElems.set(this.activeElems().filter((x) => x !== el));
        this.bus.trigger("active-element-changed", this.activeElement());
    }

    getActiveElementOf(el) {
        for (const activeElement of [...this.activeElems()].reverse()) {
            if (activeElement.contains(el)) {
                return activeElement;
            }
        }
    }
}

services.add(UIPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the ui service are removed
 * -----------------------------------------------------------------------------
 */

export const uiService = {
    start() {
        const uiPlugin = usePlugin(UIPlugin);
        const service = Object.create(uiPlugin);

        Object.defineProperty(service, "activeElement", {
            get() {
                return uiPlugin.activeElement();
            },
        });
        Object.defineProperty(service, "isBlocked", {
            get() {
                return uiPlugin.isBlocked();
            },
        });
        Object.defineProperty(service, "isSmall", {
            get() {
                return uiPlugin.isSmall();
            },
        });
        Object.defineProperty(service, "size", {
            get() {
                return uiPlugin.size();
            },
        });

        service.activateElement = uiPlugin.activateElement.bind(uiPlugin);
        service.deactivateElement = uiPlugin.deactivateElement.bind(uiPlugin);

        return service;
    },
};

registry.category("services").add("ui", uiService);
