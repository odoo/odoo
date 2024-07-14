/** @odoo-module **/

import ServiceCore from "@web_mobile/js/services/core";

import { onMounted, onPatched, onWillUnmount, useComponent } from "@odoo/owl";

/**
 * This hook provides support for executing code when the back button is pressed
 * on the mobile application of Odoo. This actually replaces the default back
 * button behavior so this feature should only be enabled when it is actually
 * useful.
 *
 * The feature is either enabled on mount or, using the `shouldEnable` function
 * argument as condition, when the component is patched. In both cases,
 * the feature is automatically disabled on unmount.
 *
 * @param {function} func the function to execute when the back button is
 *  pressed. The function is called with the custom event as param.
 * @param {function} [shouldEnable] the function to execute when the DOM is
 *  patched to check if the backbutton should be enabled or disabled ;
 *  if undefined will be enabled on mount and disabled on unmount.
 */
export function useBackButton(func, shouldEnable) {
    const component = useComponent();
    let isEnabled = false;

    /**
     * Enables the func listener, overriding default back button behavior.
     */
    function enable() {
        ServiceCore.backButtonManager.addListener(component, func);
        isEnabled = true;
    }

    /**
     * Disables the func listener, restoring the default back button behavior if
     * no other listeners are present.
     */
    function disable() {
        ServiceCore.backButtonManager.removeListener(component);
        isEnabled = false;
    }

    onMounted(() => {
        if (shouldEnable && !shouldEnable()) {
            return;
        }
        enable();
    });

    onPatched(() => {
        if (!shouldEnable) {
            return;
        }
        const shouldBeEnabled = shouldEnable();
        if (shouldBeEnabled && !isEnabled) {
            enable();
        } else if (!shouldBeEnabled && isEnabled) {
            disable();
        }
    });

    onWillUnmount(() => {
        if (isEnabled) {
            disable();
        }
    });
}
