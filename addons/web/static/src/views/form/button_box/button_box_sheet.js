import { Component, useSubEnv } from "@odoo/owl";

/**
 * Content component for the button box bottom sheet
 * This component only provides the content that will be placed
 * inside the bottom sheet container by the service.
 */
export class ButtonBoxBottomSheet extends Component {
    static template = "web.ButtonBoxBottomSheet";
    static props = {
        additionalButtons: Array,
        slots: Object,
        close: { type: Function, optional: true },
        parentEnv: { type: Object, optional: true }
    };

    setup() {
        // If parentEnv is provided, wrap the onClickViewButton to dismiss the sheet after execution
        if (this.props.parentEnv?.onClickViewButton) {
            const originalOnClickViewButton = this.props.parentEnv.onClickViewButton;

            // Create a wrapper function that calls the original function
            // and then dismisses the bottom sheet
            const wrappedOnClickViewButton = async (params) => {
                try {
                    const result = await originalOnClickViewButton(params);
                    // Dismiss the bottom sheet after the action completes
                    this.props.close?.();
                    return result;
                } catch (error) {
                    // Don't dismiss if there was an error
                    throw error;
                }
            };

            useSubEnv({
                onClickViewButton: wrappedOnClickViewButton
            });
        }
    }
}
