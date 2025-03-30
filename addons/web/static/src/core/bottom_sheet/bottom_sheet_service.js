import { registry } from "@web/core/registry";
import { BottomSheet } from "./bottom_sheet";

/**
 * Bottom Sheet Service
 *
 * Provides application-wide functionality for managing bottom sheets.
 * Keeps track of active sheets and handles proper sheet transitions.
 *
 * @type {Object}
 */
export const bottomSheetService = {
    dependencies: ["overlay"],

    /**
     * Initializes the bottom sheet service
     *
     * @param {Object} env - Environment object
     * @param {Object} dependencies - Injected dependencies
     * @param {Object} dependencies.overlay - Overlay service instance
     * @returns {Object} - Public API methods
     */
    start(env, { overlay }) {
        let nextId = 0;
        let currentSheet = null;

        /**
         * Add a new component to the bottom sheet
         *
         * @param {Component} component - Component to render in the sheet
         * @param {Object} props - Props for the component
         * @param {Object} options - Configuration options
         * @param {string} [options.title] - Sheet title
         * @param {boolean} [options.showBackBtn] - Whether to show back button
         * @param {boolean} [options.showCloseBtn] - Whether to show close button
         * @param {boolean} [options.withBodyPadding] - Whether to add padding to the body
         * @param {number} [options.initialHeightPercent] - Initial height as percentage of viewport
         * @param {number} [options.maxHeightPercent] - Maximum height as percentage of viewport
         * @param {boolean} [options.startExpanded] - Whether to start in expanded state
         * @param {string} [options.sheetClasses] - Additional CSS classes
         * @param {Function} [options.onClose] - Callback when sheet is closed
         * @param {Function} [options.onBack] - Callback when back button is pressed
         * @param {Object} [options.env] - Environment to pass to the overlay
         * @param {Object} [options.slots] - Slots to pass to the BottomSheet component
         * @returns {Function} Function to close the sheet
         */
        function add(component, props = {}, options = {}) {
            const id = nextId++;

            // Create props for the component including close function
            const componentProps = {
                ...props,
                close: () => remove(id)
            };

            // Check if component already has a BottomSheet in its template
            const hasDeclarativeSheet = (component && component.components && Object.values(component.components).some(comp => comp.name === "BottomSheet" || comp === BottomSheet));

            // If there's already an active sheet, slide it out
            if (currentSheet) {
                const sheetEl = document.querySelector(`.o_bottom_sheet[data-sheet-id="${currentSheet.id}"]`);
                if (sheetEl && sheetEl._owl?.component) {
                    sheetEl._owl.component.slideOut();
                } else if (currentSheet.removeFromDOM) {
                    currentSheet.removeFromDOM();
                }
            }

            // Determine which component to add and how to configure it
            let componentToAdd = component;
            let propsToAdd = componentProps;
            // Make a copy of options to avoid modifying the original
            let bottomSheetOptions = { ...options };

            // Check registry for custom component and options
            let registration = null;
            if (component.name) {
                registration = registry.category("bottom_sheet_components").get(component.name, false);
            }

            if (!hasDeclarativeSheet) {
                // Apply custom component from registry if available
                if (registration && registration.Component) {
                    componentToAdd = registration.Component;
                }

                // Apply custom options from registry if available
                if (registration && registration.options) {
                    bottomSheetOptions = { ...bottomSheetOptions, ...registration.options };
                }

                // Normal case - wrap with BottomSheet
                propsToAdd = {
                    id: id,
                    component: componentToAdd,
                    componentProps: componentProps,
                    title: bottomSheetOptions.title || '',
                    showBackBtn: bottomSheetOptions.showBackBtn || false,
                    showCloseBtn: bottomSheetOptions.showCloseBtn || false,
                    withBodyPadding: bottomSheetOptions.withBodyPadding !== undefined ? bottomSheetOptions.withBodyPadding : true,
                    initialHeightPercent: bottomSheetOptions.initialHeightPercent || 50,
                    maxHeightPercent: bottomSheetOptions.maxHeightPercent || 90,
                    startExpanded: bottomSheetOptions.startExpanded || false,
                    preventDismissOnContentScroll: bottomSheetOptions.preventDismissOnContentScroll || false,
                    sheetClasses: bottomSheetOptions.sheetClasses || '',
                    onClose: bottomSheetOptions.onClose,
                    onBack: bottomSheetOptions.onBack,
                    slots: bottomSheetOptions.slots || {},
                };

                // When using registry component, apply slot mappings if configured
                if (registration && registration.slots) {
                    const slotMappings = registration.slots;
                    const wrappedSlots = {};

                    // Map slots according to configuration
                    Object.entries(slotMappings).forEach(([sourceSlot, targetSlot]) => {
                        if (props[sourceSlot]) {
                            wrappedSlots[targetSlot] = props[sourceSlot];
                        }
                    });

                    // Merge with any existing slots
                    propsToAdd.slots = { ...propsToAdd.slots, ...wrappedSlots };
                }

                // Use BottomSheet as the container
                componentToAdd = BottomSheet;
            }

            // Create the sheet in the overlay
            const removeFromDOM = overlay.add(
                componentToAdd,
                propsToAdd,
                {
                    onRemove: () => {
                        // Reset current sheet if this one is being removed
                        if (currentSheet && currentSheet.id === id) {
                            currentSheet = null;
                        }

                        // Call onClose callback
                        if (bottomSheetOptions.onClose) {
                            bottomSheetOptions.onClose();
                        }
                    },
                    env: bottomSheetOptions.env // Pass the environment to overlay
                }
            );

            // Store current sheet info
            currentSheet = {
                id,
                removeFromDOM,
                component,
                options: bottomSheetOptions,
            };

            // Return a function to close the sheet
            return () => remove(id);
        }

        /**
         * Remove a sheet by ID
         *
         * @param {number} id - Sheet ID to remove
         */
        function remove(id) {
            if (!currentSheet || currentSheet.id !== id) return;

            // Get the sheet element
            const sheetEl = document.querySelector(`.o_bottom_sheet[data-sheet-id="${id}"]`);
            if (sheetEl && sheetEl._owl?.component) {
                sheetEl._owl.component.slideOut();
            } else if (currentSheet.removeFromDOM) {
                currentSheet.removeFromDOM();
            }

            // Reset current sheet
            currentSheet = null;
        }

        return { add, remove };
    }
};

registry.category("services").add("bottomSheet", bottomSheetService);
