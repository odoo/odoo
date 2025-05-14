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
        let sheetStack = [];

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
         * @param {boolean} [options.isNestedSheet] - Whether this sheet is nested under another
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

            // For nested sheets, we want to hide the current sheet visually but keep it in the DOM
            const isNestedSheet = options.isNestedSheet === true;

            // If there's already an active sheet and this is a nested sheet, hide the parent
            if (sheetStack.length > 0 && isNestedSheet) {
                // Get the current top sheet from the stack
                const currentSheet = sheetStack[sheetStack.length - 1];
                const currentSheetEl = document.querySelector(`.o_bottom_sheet[data-sheet-id="${currentSheet.id}"]`);

                if (currentSheetEl) {
                    // Mark the parent sheet to have its backdrop opacity adjusted
                    currentSheetEl.classList.add('o_bottom_sheet_parent_of_active');
                }
            } else if (sheetStack.length > 0 && !isNestedSheet) {
                // If not a nested sheet, remove previous sheets completely
                removeAllSheets();

                // Clear the stack since we're starting a new sheet chain
                sheetStack = [];
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

                // Add classes to indicate this is a nested sheet
                let additionalClasses = '';
                if (isNestedSheet) {
                    additionalClasses = 'o_bottom_sheet_nested';
                }

                // Normal case - wrap with BottomSheet
                propsToAdd = {
                    id: id,
                    component: componentToAdd,
                    componentProps: componentProps,
                    title: bottomSheetOptions.title || '',
                    showBackBtn: bottomSheetOptions.showBackBtn || (isNestedSheet && sheetStack.length > 0),
                    showCloseBtn: bottomSheetOptions.showCloseBtn || false,
                    withBodyPadding: bottomSheetOptions.withBodyPadding !== undefined ? bottomSheetOptions.withBodyPadding : true,
                    initialHeightPercent: bottomSheetOptions.initialHeightPercent || 50,
                    maxHeightPercent: bottomSheetOptions.maxHeightPercent || 90,
                    startExpanded: bottomSheetOptions.startExpanded || false,
                    preventDismissOnContentScroll: bottomSheetOptions.preventDismissOnContentScroll || false,
                    sheetClasses: `${bottomSheetOptions.sheetClasses || ''} ${additionalClasses}`.trim(),
                    onClose: bottomSheetOptions.onClose,
                    onBack: () => {
                        if (isNestedSheet && sheetStack.length > 1) {
                            // If this is a nested sheet, we want to go back to the previous sheet
                            remove(id);
                        } else if (bottomSheetOptions.onBack) {
                            // Otherwise, call the custom onBack if provided
                            bottomSheetOptions.onBack();
                        } else {
                            // Default fallback
                            remove(id);
                        }
                    },
                    slots: bottomSheetOptions.slots || {},
                    isNestedSheet: isNestedSheet,
                    removeAllSheets: () => removeAllSheets(),
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
                        // Find this sheet in the stack
                        const sheetIndex = sheetStack.findIndex(sheet => sheet.id === id);
                        if (sheetIndex !== -1) {
                            // Remove this sheet from stack
                            sheetStack.splice(sheetIndex, 1);

                            // If there's a parent sheet and this was removed, show the parent again
                            if (sheetIndex > 0 && sheetStack.length > 0) {
                                const parentSheet = sheetStack[sheetStack.length - 1];
                                const parentSheetEl = document.querySelector(`.o_bottom_sheet[data-sheet-id="${parentSheet.id}"]`);
                                if (parentSheetEl) {
                                    // Show the sheet content again
                                    const sheetContentEl = parentSheetEl.querySelector('.o_bottom_sheet_sheet');
                                    if (sheetContentEl) {
                                        sheetContentEl.classList.remove('o_bottom_sheet_hidden');
                                    }

                                    // Remove the parent marker class
                                    parentSheetEl.classList.remove('o_bottom_sheet_parent_of_active');
                                }
                            }
                        }

                        // Call onClose callback
                        if (bottomSheetOptions.onClose) {
                            bottomSheetOptions.onClose();
                        }
                    },
                    env: bottomSheetOptions.env // Pass the environment to overlay
                }
            );

            // Store sheet info in the stack
            const sheetInfo = {
                id,
                removeFromDOM,
                component,
                options: bottomSheetOptions,
            };

            sheetStack.push(sheetInfo);

            // Return a function to close the sheet
            return () => remove(id);
        }

        /**
         * Remove a sheet by ID
         *
         * @param {number} id - Sheet ID to remove
         */
        function remove(id) {
            // Find the sheet in the stack
            const sheetIndex = sheetStack.findIndex(sheet => sheet.id === id);
            if (sheetIndex === -1) return;

            // Get the sheet to remove
            const sheetToRemove = sheetStack[sheetIndex];

            // Get the sheet element
            const sheetEl = document.querySelector(`.o_bottom_sheet[data-sheet-id="${id}"]`);
            if (sheetEl && sheetEl._owl?.component) {
                sheetEl._owl.component.slideOut();
            } else if (sheetToRemove.removeFromDOM) {
                sheetToRemove.removeFromDOM();
            }

            // Remove from stack
            sheetStack.splice(sheetIndex, 1);

            // If this sheet has a parent in the stack, show the parent again
            if (sheetIndex > 0 && sheetStack.length > 0) {
                const parentIndex = sheetIndex - 1;
                if (parentIndex < sheetStack.length) {
                    const parentSheet = sheetStack[parentIndex];
                    const parentSheetEl = document.querySelector(`.o_bottom_sheet[data-sheet-id="${parentSheet.id}"]`);
                    if (parentSheetEl) {
                        // Show the sheet content again
                        const sheetContentEl = parentSheetEl.querySelector('.o_bottom_sheet_sheet');
                        if (sheetContentEl) {
                            sheetContentEl.classList.remove('o_bottom_sheet_hidden');
                        }

                        // Remove the parent marker class
                        parentSheetEl.classList.remove('o_bottom_sheet_parent_of_active');
                    }
                }
            } else {
                document.body.classList.remove("bottom-sheet-open");
            }
        }

        /**
         * Removes all sheets in the stack
         *
         * @param {boolean} [includeTopSheet=true] Whether to include the top-most sheet in removal
         */
        function removeAllSheets(includeTopSheet = true) {
            // No sheets to remove
            if (sheetStack.length === 0) return;

            // Make a copy of the stack to avoid issues while iterating
            const sheetsToRemove = [...sheetStack];

            // Get the top sheet (current active one)
            const topSheet = sheetsToRemove[sheetsToRemove.length - 1];

            // For each sheet in the stack
            for (let i = 0; i < sheetsToRemove.length; i++) {
                const sheet = sheetsToRemove[i];
                const isTopSheet = sheet.id === topSheet.id;

                // Skip the top sheet if requested
                if (isTopSheet && !includeTopSheet) {
                    continue;
                }

                // Remove all other sheets immediately
                const sheetEl = document.querySelector(`.o_bottom_sheet[data-sheet-id="${sheet.id}"]`);
                if (sheetEl && sheetEl._owl?.component) {
                    sheetEl._owl.component.slideOut(true); // true = no animation
                } else if (sheet.removeFromDOM) {
                    sheet.removeFromDOM();
                }

                // Remove from stack
                const sheetIndex = sheetStack.findIndex(s => s.id === sheet.id);
                if (sheetIndex !== -1) {
                    sheetStack.splice(sheetIndex, 1);
                }
            }

            // If we kept the top sheet, we're not clearing the stack
            if (!includeTopSheet && sheetStack.length > 0) {
                return;
            }

            // Clear the stack if we removed everything
            sheetStack = [];
            document.body.classList.remove("bottom-sheet-open");
        }

        return { add, remove, removeAllSheets };
    }
};

registry.category("services").add("bottomSheet", bottomSheetService);
