// @ts-check
/** @odoo-module native */

import { onMounted, useChildSubEnv, useComponent } from "@odoo/owl";
import { getComponentElement } from "@web/core/utils/components";

const ACTIVE_ELEMENT_SCOPE = Symbol("ui.activeElementScope");

/** @type {WeakMap<object, { el: HTMLElement | null }>} */
const OWN_SCOPES = new WeakMap();

/** @type {(node: Node) => Document | HTMLElement} */
let enclosingScopeOf = () => document;
/** @type {() => Document | HTMLElement} */
let currentActiveElement = () => document;

/**
 * @param {(node: Node) => Document | HTMLElement} resolve
 * @param {() => Document | HTMLElement} [current]
 * @returns {() => void}
 */
export function publishEnclosingScopeResolver(resolve, current = () => document) {
    enclosingScopeOf = resolve;
    currentActiveElement = current;
    return () => {
        enclosingScopeOf = () => document;
        currentActiveElement = () => document;
    };
}

/** @returns {{ el: HTMLElement | null }} */
export function useOwnedActiveElement() {
    /** @type {{ el: HTMLElement | null }} */
    const scope = { el: null };
    OWN_SCOPES.set(useComponent(), scope);
    useChildSubEnv({ [ACTIVE_ELEMENT_SCOPE]: scope });
    return scope;
}

// a component that renders a dialog mounts after that dialog took the
// active element (children mount first): the element it was mounted in
// is its scope while that element stands, exactly as a scope captured at
// registration would be. An active element a child takes later is not.
/** @returns {() => Document | HTMLElement} */
export function useActiveElementScope() {
    const component = useComponent();
    /** @type {Document | HTMLElement} */
    let mountedIn = document;
    onMounted(() => {
        mountedIn = currentActiveElement();
    });
    return () => {
        const own =
            OWN_SCOPES.get(component) ??
            /** @type {Record<symbol, { el: HTMLElement | null }>} */ (component.env)[
                ACTIVE_ELEMENT_SCOPE
            ];
        if (own?.el) {
            return own.el;
        }
        const el = getComponentElement(component);
        if (!el) {
            return document;
        }
        const enclosing = enclosingScopeOf(el);
        if (
            enclosing === document &&
            mountedIn !== document &&
            el.contains(mountedIn) &&
            mountedIn.isConnected
        ) {
            return mountedIn;
        }
        return enclosing;
    };
}
