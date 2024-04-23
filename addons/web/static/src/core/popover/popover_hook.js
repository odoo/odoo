import { Component, onWillUnmount, status, useComponent, useEnv, xml } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { omit } from "@web/core/utils/objects";

/**
 * @typedef {import("@web/core/popover/popover_service").PopoverServiceAddFunction} PopoverServiceAddFunction
 * @typedef {import("@web/core/popover/popover_service").PopoverServiceAddOptions} PopoverServiceAddOptions
 */

/**
 * @typedef PopoverHookReturnType
 * @property {(target: string | HTMLElement, props: object) => void} open
 *  - Signals the manager to open the configured popover
 *    component on the target, with the given props.
 * @property {() => void} close
 *  - Signals the manager to remove the popover.
 * @property {boolean} isOpen
 *  - Whether the popover is currently open.
 *
 * @typedef ExtraOptions
 * @property {boolean} [responsive=false]
 *  - if true, the popover will get replaced by a fullscreen dialog on small screens
 *
 * @typedef {ExtraOptions & PopoverServiceAddOptions} PopoverHookOptions
 */

/**
 * @param {PopoverServiceAddFunction} addFn
 * @param {typeof import("@odoo/owl").Component} component
 * @param {PopoverServiceAddOptions} options
 * @returns {PopoverHookReturnType}
 */
export function makePopover(addFn, component, options) {
    let removeFn = null;
    function close() {
        removeFn?.();
    }
    return {
        open(target, props) {
            close();
            const newOptions = Object.create(options);
            newOptions.onClose = () => {
                removeFn = null;
                options.onClose?.();
            };
            removeFn = addFn(target, component, props, newOptions);
        },
        close,
        get isOpen() {
            return Boolean(removeFn);
        },
    };
}

/**
 * Manages a component to be used as a popover.
 *
 * @param {typeof import("@odoo/owl").Component} component
 * @param {PopoverHookOptions} [options]
 * @returns {PopoverHookReturnType}
 */
export function usePopover(component, options = {}) {
    const popoverService = useService("popover");
    const dialogService = useService("dialog");
    const env = useEnv();
    const owner = useComponent();
    const shouldBeResponsive = options.responsive ?? false;
    const newOptions = omit(options, "responsive");
    newOptions.onClose = () => {
        if (status(owner) !== "destroyed") {
            options.onClose?.();
        }
    };
    const addFn = (target, comp, props, options) => {
        if (shouldBeResponsive && env.isSmall) {
            return dialogService.add(
                PopoverInDialog,
                { component: comp, componentProps: props },
                { onClose: options.onClose }
            );
        }
        return popoverService.add(target, comp, props, options);
    };
    const popover = makePopover(addFn, component, newOptions);
    onWillUnmount(popover.close);
    return popover;
}

class PopoverInDialog extends Component {
    static components = { Dialog };
    static props = ["close", "component", "componentProps"];
    static template = xml`
        <Dialog footer="false">
            <t t-component="props.component" t-props="componentProps"/>
        </Dialog>
    `;
    get componentProps() {
        return { ...this.props.componentProps, close: this.props.close };
    }
}
