import { registry } from "@web/core/registry";
import { loadJS } from "@web/core/assets";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

async function paypalOnboardingAction(env, action) {
    const providerId = action.params.provider_id;
    const response = await rpc("/payment/paypal/init_onboarding", { provider_id: providerId });

    if (response.error) {
        env.services.notification.add(response.error, { type: "danger" });
        return;
    }

    const { paypal_url: paypalUrl, partner_sdk_url: partnerSdkUrl } = response;

    window.onboardedCallback = async function (authCode, sharedId) {
        let result;
        try {
            result = await rpc("/payment/paypal/oauth/return", {
                auth_code: authCode,
                shared_id: sharedId,
                provider_id: providerId
            });
        } catch {
            result = { error: _t("Something went wrong during PayPal onboarding. Please try again.") };
        }
        if (result.error_url) {
            window.location.assign(result.error_url);
            return;
        }
        if (result.error) {
            env.services.notification.add(result.error, { type: "danger" });
            return;
        }
        env.services.action.doAction("soft_reload");
    };

    const onboardBtn = document.getElementById("partner-js");
    onboardBtn.href = `${paypalUrl}&displayMode=minibrowser`;

    await loadJS(partnerSdkUrl);
    await new Promise((resolve) => {
        let attempts = 0;
        const checkInterval = setInterval(() => {
            attempts++;
            if (window.PAYPAL || attempts > 100) {
                clearInterval(checkInterval);
                setTimeout(resolve, 50);
            }
        }, 50);
    });
    onboardBtn.click();
}

registry.category("actions").add("paypal_onboarding_client_action", paypalOnboardingAction);
