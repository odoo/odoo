// @ts-check
/** @odoo-module native */

import { markRaw, reactive } from "@odoo/owl";
import { rootIdOf } from "@web/ui/overlay/root_id";

const SERVICE_OPTIONS = ["env", "onClose", "sequence", "useBottomSheet"];

const PRESENTER_SUPPLIED = ["close", "component", "componentProps", "slots", "target"];

/** @type {Set<import("@odoo/owl").ComponentConstructor>} */
const PRESENTED_COMPONENTS = new Set();

/** @returns {Set<string>} */
function acceptedOptions() {
    const accepted = new Set(SERVICE_OPTIONS);
    for (const component of PRESENTED_COMPONENTS) {
        for (const name of Object.keys(/** @type {any} */ (component).props ?? {})) {
            accepted.add(name);
        }
    }
    for (const name of PRESENTER_SUPPLIED) {
        accepted.delete(name);
    }
    return accepted;
}

/**
 * @param {string} scope
 * @param {object} options
 * @param {Set<string>} accepted
 */
export function warnUnknownOptions(scope, options, accepted) {
    for (const key in options) {
        if (!accepted.has(key)) {
            console.warn(`[${scope}] unknown option "${key}"; it will be ignored.`);
        }
    }
}

/** @type {Record<string, any>} */
export const PRESENTED_PROPS = {
    close: { type: Function },
    componentProps: { optional: true, type: Object },

    class: { optional: true },
    id: { optional: true, type: String },
    role: { optional: true, type: String },

    closeOnClickAway: { optional: true, type: Function },
    closeOnEscape: { optional: true, type: Boolean },
    setActiveElement: { optional: true, type: Boolean },

    ref: { optional: true, type: Function },

    presentation: { optional: true, type: Object },
};

/**
 * @param {boolean | ((target: HTMLElement) => boolean) | undefined} value
 * @returns {(target: HTMLElement) => boolean}
 */
function asPredicate(value) {
    return typeof value === "function" ? value : () => value ?? true;
}

/**
 * @param {any} options
 * @returns {object}
 */
function commonProps(options) {
    return {
        class: options.class,
        closeOnClickAway: asPredicate(options.closeOnClickAway),
        closeOnEscape: options.closeOnEscape,
        id: options.id,
        ref: options.ref,
        role: options.role,
        setActiveElement: options.setActiveElement,
    };
}

/**
 * @param {object} config
 * @param {any} config.overlay
 * @param {import("@odoo/owl").ComponentConstructor} config.component
 * @param {(options: any, target: HTMLElement) => object} config.toProps
 * @param {string} [config.scope]
 * @param {(options: any) => void} [config.onOpen]
 * @param {() => void} [config.onClosed]
 * @returns {(target: HTMLElement, component: any, props?: object, options?: any) => (removeParams?: any) => Promise<void>}
 */
export function makeOverlayPresenter({
    overlay,
    component,
    toProps,
    scope,
    onOpen,
    onClosed,
}) {
    PRESENTED_COMPONENTS.add(component);
    return (target, hostedComponent, props = {}, options = {}) => {
        warnUnknownOptions(scope ?? "overlay", options, acceptedOptions());
        if (target instanceof Node && !target.isConnected) {
            const closed = Promise.resolve().then(() => options.onClose?.());
            return () => closed;
        }
        const presentation = reactive({ isClosing: false });
        const remove = overlay.add(
            component,
            {
                ...commonProps(options),
                ...toProps(options, target),
                component: hostedComponent,
                componentProps: markRaw(props),
                presentation,
                close: (/** @type {any} */ removeParams) => remove(removeParams),
            },
            {
                env: options.env,
                sequence: options.sequence,
                rootId: rootIdOf(target),
                onRemove: async (/** @type {any} */ removeParams) => {
                    presentation.isClosing = true;
                    try {
                        await options.onClose?.(removeParams);
                    } finally {
                        onClosed?.();
                    }
                },
            },
        );
        onOpen?.(options);
        return remove;
    };
}
