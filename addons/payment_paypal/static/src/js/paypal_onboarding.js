import { registry } from "@web/core/registry";
import { loadJS } from "@web/core/assets";
import { rpc } from "@web/core/network/rpc";

async function paypalOnboardingAction(env, action) {
    const providerId = action.params.provider_id;
    const response = await rpc("/payment/paypal/init_onboarding", {provider_id: providerId});

    if (response.error) {
        env.services.notification.add(response.error, { type: "danger" });
        return;
    }

    const paypalUrl = response.paypal_url;
    const csrfState = response.csrf_state;

    window.onboardedCallback = function(authCode, sharedId) {
        const params = new URLSearchParams();
        params.append('authCode', authCode);
        params.append('sharedId', sharedId);
        params.append('state', csrfState);

        if (window.__paypalPopupWindow) {
            const checkClosedInterval = setInterval(() => {
                if (window.__paypalPopupWindow.closed) {
                    clearInterval(checkClosedInterval);
                    window.location.assign(`/payment/paypal/oauth/return?${params.toString()}`);
                }
            }, 500);
        } else {
            window.location.assign(`/payment/paypal/oauth/return?${params.toString()}`);
        }
    };
    let hiddenBtn = document.getElementById('paypal-hidden-onboarding-btn');

    if (!hiddenBtn) {
        hiddenBtn = document.createElement('a');
        hiddenBtn.id = 'paypal-hidden-onboarding-btn';
        hiddenBtn.setAttribute('data-paypal-onboard-complete', 'onboardedCallback');
        hiddenBtn.setAttribute('data-paypal-button', 'true');
        hiddenBtn.setAttribute('target', '_blank');
        hiddenBtn.style.display = 'none';
        document.body.appendChild(hiddenBtn);
    }

    hiddenBtn.href = paypalUrl + "&displayMode=minibrowser";

    await loadJS("https://www.sandbox.paypal.com/webapps/merchantboarding/js/lib/lightbox/partner.js");

    setTimeout(() => {
        const originalOpen = window.open;
        window.open = function(url, target, features) {
            const popup = originalOpen.call(window, url, target, features);
            window.__paypalPopupWindow = popup;
            return popup;
        };

        hiddenBtn.click();
        window.open = originalOpen;
    }, 200);
}

registry.category("actions").add("paypal_onboarding_client_action", paypalOnboardingAction);
