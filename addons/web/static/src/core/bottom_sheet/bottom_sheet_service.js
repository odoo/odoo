import { Component, markRaw, reactive, useChildSubEnv, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { BottomSheetContainer } from "./bottom_sheet_container";

class BottomSheetWrapper extends Component {
    static template = xml`<t t-component="props.subComponent" t-props="props.subProps" />`;
    static props = ["*"];
    setup() {
        useChildSubEnv({ bottomSheetData: this.props.subEnv });
    }
}

export const bottomSheetService = {
    dependencies: ["overlay"],
    start(env, { overlay }) {
        // Single source of truth - a reactive object with active sheet and a stack of sheets
        const state = reactive({
            activeSheet: null,
            sheetStack: [],
            isInitializing: false  // Flag to prevent auto-close during initialization
        });

        let nextId = 0;
        let containerRemove = null;

        /**
         * Create container if it doesn't exist
         */
        const ensureContainer = () => {
            if (!containerRemove) {
                containerRemove = overlay.add(
                    BottomSheetContainer,
                    { state },
                    {
                        onRemove: () => {
                            containerRemove = null;
                            document.body.classList.remove("bottom-sheet-open");
                        }
                    }
                );
                document.body.classList.add("bottom-sheet-open");
            }
        };

        /**
         * Add a new sheet
         */
        const add = (sheetComponent, props, options = {}) => {
            // Generate sheet ID and create close function
            const id = nextId++;
            const closeFn = () => remove(id);

            // Create sheet props with close function
            const sheetProps = { ...props, close: closeFn };

            // Extract bottom sheet configuration from various sources with this precedence:
            // 1. Explicit options to the service (highest priority)
            // 2. The bottomSheetConfig property from component props (if exists)
            // 3. Default values (lowest priority)

            // First, establish default values
            let visibleInitialMax = 40;
            let visibleExtended = 90;
            let forceExtendedFullHeight = false;
            let sheetClasses = '';

            // Next, check if component included bottomSheetConfig
            if (props.bottomSheetConfig) {
                visibleInitialMax = props.bottomSheetConfig.visibleInitialMax ?? visibleInitialMax;
                visibleExtended = props.bottomSheetConfig.visibleExtended ?? visibleExtended;
                forceExtendedFullHeight = props.bottomSheetConfig.forceExtendedFullHeight ?? forceExtendedFullHeight;
                sheetClasses = props.bottomSheetConfig.sheetClasses ?? sheetClasses;
            }

            // Finally, apply options passed directly to service (highest priority)
            visibleInitialMax = options.visibleInitialMax ?? visibleInitialMax;
            visibleExtended = options.visibleExtended ?? visibleExtended;
            forceExtendedFullHeight = options.forceExtendedFullHeight ?? forceExtendedFullHeight;
            sheetClasses = options.sheetClasses ?? sheetClasses;

            // Create sheet object
            const sheet = {
                id,
                component: sheetComponent,
                props: markRaw(sheetProps),
                close: closeFn,
                dismiss: closeFn,
                onClose: options.onClose,
                sheetClasses,
                visibleInitialMax,
                visibleExtended,
                forceExtendedFullHeight,
                subEnv: reactive({
                    id,
                    close: closeFn,
                    dismiss: closeFn,
                })
            };

            // Ensure container exists
            ensureContainer();

            // Prevent auto-close during initialization
            state.isInitializing = true;

            // Add sheet to stack and set as active
            state.sheetStack.push(sheet);
            state.activeSheet = sheet;

            // After a small delay, allow auto-close
            setTimeout(() => {
                state.isInitializing = false;
            }, 500);

            return closeFn;
        };

        /**
         * Remove a sheet by ID
         */
        function remove(id) {
            // Ignore removal during initialization phase
            if (state.isInitializing && state.activeSheet?.id === id) {
                return;
            }

            // Find the sheet in the stack
            const sheetIndex = state.sheetStack.findIndex(sheet => sheet.id === id);
            if (sheetIndex !== -1) {
                const sheet = state.sheetStack[sheetIndex];

                // Remove the sheet from the stack
                state.sheetStack.splice(sheetIndex, 1);

                // If removing the active sheet, activate the previous sheet
                if (state.activeSheet?.id === id) {
                    state.activeSheet = state.sheetStack.length > 0
                        ? state.sheetStack[state.sheetStack.length - 1]
                        : null;
                }

                // If no more sheets, remove the container
                if (state.sheetStack.length === 0 && containerRemove) {
                    containerRemove();
                    containerRemove = null;
                }

                // Call onClose callback
                sheet.onClose?.();
            }
        }

        return { add, remove };
    },
};

registry.category("services").add("bottomSheet", bottomSheetService);