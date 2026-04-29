import { registry } from "@web/core/registry";
import { RPCErrorDialog } from "@web/core/errors/error_dialogs";
import { loadJS } from "@web/core/assets";
import { rpc } from "@web/core/network/rpc";

/**
 * Run the PayPal seller onboarding in a PayPal-hosted mini browser.
 *
 * The onboarding is driven by PayPal's partner SDK: it opens the mini browser on the onboarding
 * URL, then calls back into Odoo with the OAuth values once the seller has linked their account.
 *
 * @param {Object} env - The environment of the client action
 * @param {Object} action - The client action
 * @return {void}
 */
async function paypalOnboardingAction(env, action) {
    // Fetch the URLs of the merchant-specific onboarding page and of the partner SDK
    const providerId = action.params.provider_id;
    const response = await rpc("/payment/paypal/oauth/init", { provider_id: providerId });
    const { paypal_url: paypalUrl, partner_sdk_url: partnerSdkUrl } = response;

    // Link the SDK's anchor to the onboarding page and register its finalization callback
    const onboardBtn = document.getElementById("o_paypal_onboarding_button");
    onboardBtn.href = paypalUrl;
    window.paypalOnboardedCallback = async (authCode, sharedId) => {
        try {
            await rpc("/payment/paypal/oauth/finalize", {
                auth_code: authCode,
                shared_id: sharedId,
                provider_id: providerId
            });
        } catch (error) {
            // Manually catch RPC errors to prevent the SDK handler from consuming them, then
            // display them in the dialog the error service would have used.
            env.services.dialog.add(RPCErrorDialog, { ...error, traceback: error.stack});
            return;  // Don't reload, as `doAction` closes all the open dialogs
        }
        env.services.action.doAction("soft_reload");  // Show the account linked status
    };

    // Wait for `window.PAYPAL` to exist before clicking the anchor, since `loadJS` resolves before
    // the SDK is fully hooked on the page.
    await loadJS(partnerSdkUrl);
    await new Promise(resolve => {
        let attempts = 0;
        const checkInterval = setInterval(() => {
            attempts++;
            if (window.PAYPAL || attempts > 100) {
                clearInterval(checkInterval);
                setTimeout(resolve, 50);
            }
        }, 50);  // Wait up to five seconds
    });

    // Open the mini browser; the seller already clicked "Connect"
    onboardBtn.click();
}

registry.category("actions").add("paypal_onboarding_client_action", paypalOnboardingAction);
