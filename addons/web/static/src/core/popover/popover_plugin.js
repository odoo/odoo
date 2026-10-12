import { markRaw, t, Plugin, usePlugin, assertType } from "@odoo/owl";
import { Popover } from "@web/core/popover/popover";
import { registry } from "@web/core/registry";
import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
import { services } from "@web/core/services";

export const PopoverOptionSchema = t.object({
    animation: t.boolean().optional(),
    arrow: t.boolean().optional(),
    closeOnClickAway: t.or([t.boolean(), t.function()]).optional(),
    closeOnEscape: t.boolean().optional(),
    fixedPosition: t.boolean().optional(),
    holdOnHover: t.boolean().optional(),
    onClose: t.function().optional(),
    onPositioned: t.function().optional(),
    popoverClass: t.or([t.string(), t.object()]).optional(),
    role: t.string().optional(),
    scope: t.object().optional(),
    sequence: t.number().optional(),
    setActiveElement: t.boolean().optional(),
    shrink: t.boolean().optional(),
    position: t.string().optional(),
    ref: t.signal().optional(), // signal ref filled with the popover element
});

export class PopoverPlugin extends Plugin {
    /** @private */
    overlay = usePlugin(OverlayPlugin);

    /**
     * Signals the manager to add a popover.
     *
     * @param {HTMLElement} target
     * @param {typeof import("@odoo/owl").Component} component
     * @param {object} [props]
     * @param {PopoverOptionSchema} [options]
     * @returns {() => void}
     */
    add(target, component, props = {}, options = {}) {
        assertType(options, PopoverOptionSchema);
        const closeOnClickAway =
            typeof options.closeOnClickAway === "function"
                ? options.closeOnClickAway
                : () => options.closeOnClickAway ?? true;
        const remove = this.overlay.add(
            Popover,
            {
                target,
                close: () => remove(),
                closeOnClickAway,
                closeOnEscape: options.closeOnEscape,
                component,
                componentProps: markRaw(props),
                shrink: options.shrink,
                ref: options.ref,
                class: options.popoverClass,
                animation: options.animation,
                arrow: options.arrow,
                role: options.role,
                position: options.position,
                onPositioned: options.onPositioned,
                fixedPosition: options.fixedPosition,
                holdOnHover: options.holdOnHover,
                setActiveElement: options.setActiveElement ?? true,
            },
            {
                scope: options.scope,
                onRemove: options.onClose,
                rootId: target.getRootNode()?.host?.id,
                sequence: options.sequence,
            }
        );

        return remove;
    }
}

services.add(PopoverPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the popover service are removed
 * -----------------------------------------------------------------------------
 */
export const popoverService = {
    start() {
        return usePlugin(PopoverPlugin);
    },
};

registry.category("services").add("popover", popoverService);
