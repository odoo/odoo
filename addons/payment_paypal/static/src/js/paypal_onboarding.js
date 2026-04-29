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

    const { paypal_url: paypalUrl, csrf_state: csrfState, partner_js_url: partnerJsUrl } = response;

    window.onboardedCallback = async function (authCode, sharedId) {
        let result;
        try {
            result = await rpc("/payment/paypal/oauth/return", {
                auth_code: authCode,
                shared_id: sharedId,
                state: csrfState,
            });
        } catch {
            result = { error: _t("Something went wrong during PayPal onboarding. Please try again.") };
        }
        if (result.error) {
            env.services.notification.add(result.error, { type: "danger" });
            return;
        }
        env.services.action.doAction("soft_reload");
    };

    let onboardBtn = document.getElementById("partner-js");
    if (!onboardBtn) {
        onboardBtn = document.createElement("a");
        onboardBtn.id = "partner-js";
        onboardBtn.setAttribute("data-paypal-onboard-complete", "onboardedCallback");
        onboardBtn.setAttribute("data-paypal-button", "true");
        onboardBtn.setAttribute("target", "_blank");
        document.body.appendChild(onboardBtn);
    }
    onboardBtn.href = `${paypalUrl}&displayMode=minibrowser`;

    await loadJS(partnerJsUrl);
    // Give partner.js time to load its follow-up script and wire the button before clicking
    await new Promise((resolve) => setTimeout(resolve, 500));
    onboardBtn.click();
}

registry.category("actions").add("paypal_onboarding_client_action", paypalOnboardingAction);
