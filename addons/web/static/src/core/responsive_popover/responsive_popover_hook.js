import { onWillUnmount, status, useComponent, useEnv } from "@odoo/owl";
import { makePopover, usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { PopoverInDialog } from "./popover_in_dialog";

/**
 * Same as usePopover, but replaces the popover by a dialog when display size is small.
 *
 * @param {typeof import("@odoo/owl").Component} component
 * @param {import("@web/core/popover/popover_service").PopoverServiceAddOptions} [options]
 * @returns {import("@web/core/popover/popover_hook").PopoverHookReturnType}
 */
export function useResponsivePopover(dialogTitle, component, options = {}) {
    const dialogService = useService("dialog");
    const env = useEnv();
    const owner = useComponent();
    const popover = usePopover(component, options);
    const onClose = () => {
        if (status(owner) !== "destroyed") {
            options.onClose?.();
        }
    };
    const dialogAddFn = (_, comp, props, options) => dialogService.add(comp, props, options);
    const popoverInDialog = makePopover(dialogAddFn, PopoverInDialog, { onClose });
    const reponsivePopover = {
        open: (target, props) => {
            if (env.isSmall) {
                popoverInDialog.open(target, {
                    component: component,
                    componentProps: props,
                    dialogTitle,
                });
            } else {
                popover.open(target, props);
            }
        },
        close: () => {
            popover.close();
            popoverInDialog.close();
        },
        get isOpen() {
            return popover.isOpen || popoverInDialog.isOpen;
        },
    };
    onWillUnmount(reponsivePopover.close);
    return reponsivePopover;
}
