/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { session } from '@web/session';
import { OnboardingBanner } from "@web/views/onboarding_banner";

patch(OnboardingBanner.prototype, {
    async loadBanner(bannerRoute, { force } = {}) {
        if (bannerRoute.startsWith("/onboarding/") && !session.onboarding_to_display?.includes(bannerRoute.slice(12))) {
            return;
        }
        return super.loadBanner(bannerRoute, { force });
    }
})
