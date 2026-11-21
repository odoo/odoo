import { isIOS, isMobileOS } from "@web/core/browser/feature_detection";
import { registry } from "@web/core/registry";
import { RegistrationWallet } from "@website_event_wallet/interactions/registration_wallet";

export class AppleWallet extends RegistrationWallet {
    static selector = '.o_website_event_wallet[data-provider-code="apple"]';

    isVisible() {
        return super.isVisible() && isMobileOS() && isIOS();
    }
}

registry.category("public.interactions").add("website_event_wallet.apple", AppleWallet);
