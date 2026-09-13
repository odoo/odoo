// @ts-check
/** @odoo-module native */

import { onWillUnmount, status, useComponent } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { reportUncaught } from "@web/core/errors/error_utils";
import { useService } from "@web/core/utils/hooks";

/** @import { PopoverServiceAddFunction, PopoverServiceAddOptions } from "@web/ui/popover/popover_service" */

const log = makeLogger("web.ui.popover.hook");

/**
 * @typedef PopoverHookReturnType
 * @property {(target: string | HTMLElement, props: object) => void} open
 * @property {(removeParams?: any) => Promise<void> | undefined} close
 * @property {boolean} isOpen
 */

/**
 * @param {PopoverServiceAddFunction} addFn
 * @param {import("@odoo/owl").ComponentConstructor<any, any>} component
 * @param {PopoverServiceAddOptions} options
 * @returns {PopoverHookReturnType}
 */
export function makePopover(addFn, component, options) {
    /** @type {{ remove?: (removeParams?: any) => Promise<void> } | null} */
    let current = null;
    function close(/** @type {any} */ removeParams = undefined) {
        return current?.remove?.(removeParams);
    }
    return {
        open(target, props) {
            const previous = current;
            const opening = {};
            current = opening;
            previous?.remove?.().catch(reportUncaught);
            // Closing the previous instance can synchronously open a newer one.
            if (current !== opening) {
                log.lifecycle("superseded");
                return;
            }
            const newOptions = Object.create(options);
            newOptions.onClose = (/** @type {any} */ removeParams) => {
                log.lifecycle("closed", { current: current === opening });
                if (current === opening) {
                    current = null;
                }
                return options.onClose?.(removeParams);
            };
            try {
                opening.remove = addFn(
                    /** @type {any} */ (target),
                    component,
                    props,
                    newOptions,
                );
            } catch (error) {
                if (current === opening) {
                    current = null;
                }
                throw error;
            }
        },
        close,
        get isOpen() {
            return Boolean(current);
        },
    };
}

/**
 * @param {import("@odoo/owl").ComponentConstructor<any, any>} component
 * @param {PopoverServiceAddOptions & {useBottomSheet?: boolean | (() => boolean)}} [options]
 * @returns {PopoverHookReturnType}
 */
export function usePopover(component, options = {}) {
    const popoverService = useService("popover");
    const owner = useComponent();

    const { useBottomSheet } = options;
    const wantsBottomSheet =
        typeof useBottomSheet === "function"
            ? useBottomSheet
            : () => Boolean(useBottomSheet);
    const add = (/** @type {any[]} */ ...args) => {
        // eslint-disable-next-line no-restricted-syntax
        const sheetService = owner.env.services.bottom_sheet;
        const service = (wantsBottomSheet() && sheetService) || popoverService;
        return service.add(...args);
    };

    const newOptions = Object.create(options);
    newOptions.onClose = (/** @type {any} */ removeParams) => {
        if (status(owner) !== "destroyed") {
            return options.onClose?.(removeParams);
        }
    };
    const popover = makePopover(add, component, newOptions);
    onWillUnmount(() => popover.close()?.catch(reportUncaught));
    return popover;
}
