import { registry } from "@web/core/registry";
import { BottomSheet } from "./bottom_sheet";

export const bottomSheetService = {
    dependencies: ["overlay"],

    start(env, { overlay }) {
        let nextId = 0;
        let currentSheet = null;

        /**
         * Add a new component to the bottom sheet
         *
         * @param {Component} component - Component to render in the sheet
         * @param {Object} props - Props for the component
         * @param {Object} options - Configuration options
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

            // Determine which component to add
            let componentToAdd = component;
            let propsToAdd = componentProps;

            if (!hasDeclarativeSheet) {
                // Normal case - wrap with BottomSheet
                componentToAdd = BottomSheet;
                propsToAdd = {
                    id: id,
                    component,
                    componentProps: componentProps,
                    title: options.title || '',
                    showBackBtn: options.showBackBtn || false,
                    showCloseBtn: options.showCloseBtn || false,
                    withBodyPadding: options.withBodyPadding !== undefined ? options.withBodyPadding : true,
                    initialHeightPercent: options.initialHeightPercent || 50,
                    maxHeightPercent: options.maxHeightPercent || 90,
                    startExpanded: options.startExpanded || false,
                    sheetClasses: options.sheetClasses || '',
                    onClose: options.onClose,
                    onBack: options.onBack,
                };
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
                        if (options.onClose) {
                            options.onClose();
                        }
                    },
                    env: options.env // Pass the environment to overlay
                }
            );

            // Store current sheet info
            currentSheet = {
                id,
                removeFromDOM,
                component,
                options,
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
