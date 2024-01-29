import { loadCSS, loadJS } from "@web/core/assets";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { useActionLinks } from "@web/views/view_hook";

import { Component, markup, onWillStart, useRef, xml } from "@odoo/owl";
import { useTransition } from "@web/core/transition";

export class OnboardingBanner extends Component {
    static template = xml`<div t-if="transition.shouldMount" t-attf-class="o_onboarding_container w-100 {{transition.className}}" t-ref="onboardingContainer" t-on-click="handleActionLinks" t-out="bannerHTML"/>`;
    static props = {};

    setup() {
        this.onboardingContainerRef = useRef("onboardingContainer");
        const resModel = "searchModel" in this.env ? this.env.searchModel.resModel : undefined;
        this._handleActionLinks = useActionLinks({
            resModel,
            reload: async () => {
                this.bannerHTML = await this.loadBanner(this.env.config.bannerRoute);
                this.render();
            },
        });
        this.transition = useTransition({
            name: "o-vertical-slide",
            initialVisibility: true,
            leaveDuration: 400,
        });
        this.handleActionLinks = (event) => {
            if (event.target.dataset.oHideBanner) {
                const container = this.onboardingContainerRef.el;
                container.style.height = `${container.getBoundingClientRect().height}px`;
                this.transition.shouldMount = false;
            }
            this._handleActionLinks(event);
        };

        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        this.bannerHTML = await this.loadBanner(this.env.config.bannerRoute);
    }

    async loadBanner(bannerRoute) {
        let response = await rpc(bannerRoute, { context: user.context });
        if (response.code === 503) {
            // Sent by Onboarding Controller when rare concurrent `create` transactions occur
            response = await rpc(bannerRoute, { context: user.context });
        }
        if (!response.html) {
            return;
        }

        const banner = new DOMParser().parseFromString(response.html, "text/html");
        await Promise.all([
            ...[...banner.querySelectorAll(`script[type="text/javascript"]`)].map((el) => {
                el.remove();
                return loadJS(el.getAttribute("src"));
            }),
            ...[...banner.querySelectorAll(`link[rel="stylesheet"]`)].map((el) => {
                el.remove();
                return loadCSS(el.getAttribute("href"));
            }),
        ]);
        return markup(new XMLSerializer().serializeToString(banner));
    }
}
