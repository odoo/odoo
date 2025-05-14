import { markRaw } from "@odoo/owl";
import { Popover } from "@web/core/popover/popover";
import { registry } from "@web/core/registry";

/**
 * @typedef {{
 *   animation?: Boolean;
 *   arrow?: Boolean;
 *   closeOnClickAway?: boolean | (target: HTMLElement) => boolean;
 *   closeOnEscape?: boolean;
 *   env?: object;
 *   fixedPosition?: boolean;
 *   onClose?: () => void;
 *   onPositioned?: import("@web/core/position/position_hook").UsePositionOptions["onPositioned"];
 *   popoverClass?: string;
 *   popoverRole?: string;
 *   position?: import("@web/core/position/position_hook").UsePositionOptions["position"];
 *   ref?: Function;
 *   useBottomSheet?: boolean;
 *   title?: string;
 *
 *   // Bottom sheet specific options
 *   sheetClasses?: string;
 *   initialHeightPercent?: number;
 *   maxHeightPercent?: number;
 *   startExpanded?: boolean;
 *   preventDismissOnContentScroll?: boolean;
 * }} PopoverServiceAddOptions
 *
 * @typedef {ReturnType<popoverService["start"]>["add"]} PopoverServiceAddFunction
 */

export const popoverService = {
    dependencies: ["overlay", "bottomSheet", "ui"],
    start(_, { overlay, bottomSheet, ui }) {
        /**
         * Signals the manager to add a popover.
         *
         * @param {HTMLElement} target
         * @param {typeof import("@odoo/owl").Component} component
         * @param {object} [props]
         * @param {PopoverServiceAddOptions} [options]
         * @returns {() => void}
         */
        const add = (target, component, props = {}, options = {}) => {
            // Check if we should use a bottom sheet based on screen size and options
            const shouldUseBottomSheet = ui.isSmall && options.useBottomSheet !== false;

            if (shouldUseBottomSheet) {
                // Use bottom sheet instead of popover for mobile
                return addWithBottomSheet(target, component, props, options);
            }

            // Standard popover behavior for non-mobile or when explicitly disabled
            const closeOnClickAway =
                typeof options.closeOnClickAway === "function"
                    ? options.closeOnClickAway
                    : () => options.closeOnClickAway ?? true;
            const remove = overlay.add(
                Popover,
                {
                    target,
                    close: () => remove(),
                    closeOnClickAway,
                    closeOnEscape: options.closeOnEscape,
                    component,
                    componentProps: markRaw(props),
                    ref: options.ref,
                    class: options.popoverClass,
                    animation: options.animation,
                    arrow: options.arrow,
                    role: options.popoverRole,
                    position: options.position,
                    onPositioned: options.onPositioned,
                    fixedPosition: options.fixedPosition,
                    holdOnHover: options.holdOnHover,
                    setActiveElement: options.setActiveElement ?? true,
                },
                {
                    env: options.env,
                    onRemove: options.onClose,
                    rootId: target.getRootNode()?.host?.id,
                }
            );

            return remove;
        };

        /**
         * Add a popover using BottomSheet on mobile devices
         *
         * @param {HTMLElement} target
         * @param {typeof import("@odoo/owl").Component} component
         * @param {object} props
         * @param {PopoverServiceAddOptions} options
         * @returns {() => void}
         */
        const addWithBottomSheet = (target, component, props, options) => {
            // Check if this is a nested popover/dropdown
            const isNestedSheet = Boolean(target.closest('.o_bottom_sheet'));

            // Prepare component props with close function
            const componentProps = {
                ...props,
                close: () => remove(),
            };

            // Configure bottom sheet options based on popover options
            const bottomSheetOptions = {
                title: options.title || '',
                withBodyPadding: true,
                initialHeightPercent: options.initialHeightPercent || 50,
                maxHeightPercent: options.maxHeightPercent || 90,
                startExpanded: options.startExpanded || false,
                preventDismissOnContentScroll: options.preventDismissOnContentScroll || false,
                sheetClasses: options.sheetClasses || '',
                onClose: options.onClose,
                env: options.env,
                slots: {},
                isNestedSheet: isNestedSheet,  // Pass the nested status to bottom sheet service
                showBackBtn: isNestedSheet,    // Show back button for nested sheets
            };

            // Check if there's a mobile-specific component to use instead
            let componentToUse = component;
            let registration = null;

            // Look up in the registry if there's a mobile alternative
            if (component.name) {
                registration = registry.category("bottom_sheet_components").get(component.name, false);
                if (registration && registration.Component) {
                    componentToUse = registration.Component;

                    // Apply custom options from registry if available
                    if (registration.options) {
                        Object.assign(bottomSheetOptions, registration.options);
                    }

                    // Apply slot mappings if configured
                    if (registration.slots) {
                        // Process slot mappings
                        Object.entries(registration.slots).forEach(([sourceSlot, targetSlot]) => {
                            if (props[sourceSlot]) {
                                bottomSheetOptions.slots[targetSlot] = props[sourceSlot];
                            }
                        });
                    }
                }
            }

            // Create bottom sheet with the appropriate component
            const remove = bottomSheet.add(
                componentToUse,
                componentProps,
                bottomSheetOptions
            );

            return remove;
        };

        return { add };
    },
};

registry.category("services").add("popover", popoverService);
