import { assertType, markRaw, Plugin, signal, t, useEffect, usePlugin } from "@odoo/owl";
import { BottomSheet } from "@web/core/bottom_sheet/bottom_sheet";
import { registry } from "@web/core/registry";
import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
import { services } from "@web/core/services";

const BottomSheetOptionSchema = t.object({
    scope: t.object().optional(),
    onClose: t.function().optional(),
    class: t.or([t.string(), t.object()]).optional(),
    role: t.string().optional(),
    ref: t.signal().optional(), // signal ref filled with the sheet body element
    useBottomSheet: t.boolean().optional(),
});

export class BottomSheetPlugin extends Plugin {
    /** @private */
    overlay = usePlugin(OverlayPlugin);

    /** @private */
    bottomSheetCount = signal(0);

    setup() {
        useEffect(() => {
            document.body.classList.toggle("bottom-sheet-open", this.bottomSheetCount() >= 1);
        });
    }

    /**
     * @param {HTMLElement} target
     * @param {typeof import("@odoo/owl").Component} component
     * @param {object} [props]
     * @param {BottomSheetOptionSchema} [options]
     * @returns {() => void}
     */
    add(target, component, props = {}, options = {}) {
        assertType(options, BottomSheetOptionSchema);
        const remove = this.overlay.add(
            BottomSheet,
            {
                close: () => remove(),
                component,
                componentProps: markRaw(props),
                ref: options.ref,
                class: options.class,
                role: options.role,
            },
            {
                scope: options.scope,
                onRemove: (...args) => {
                    this.bottomSheetCount.set(this.bottomSheetCount() - 1);
                    return options.onClose?.(...args);
                },
                rootId: target.getRootNode()?.host?.id,
            }
        );
        this.bottomSheetCount.set(this.bottomSheetCount() + 1);

        return remove;
    }
}

services.add(BottomSheetPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the bottomSheet service are removed
 * -----------------------------------------------------------------------------
 */
export const bottomSheetService = {
    start() {
        return usePlugin(BottomSheetPlugin);
    },
};

registry.category("services").add("bottom_sheet", bottomSheetService);
