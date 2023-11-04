/**@odoo-module */

import { loadCSS, loadJS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
import { useActionLinks } from "@web/views/view_hook";

import { Component, useState, markup, onWillStart, useRef, xml } from "@odoo/owl";
import { useTransition } from "@web/core/transition";

export class OnboardingBanner extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.user = useService("user");
        this.state = useState({})
        this.onboardingContainerRef = useRef("onboardingContainer");
        const resModel = "searchModel" in this.env ? this.env.searchModel.resModel : undefined;
        this._handleActionLinks = useActionLinks({
            resModel,
            reload: async () => {
                this.state.bannerHTML = await this.loadBanner(this.env.config.bannerRoute);
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
        this.loadBanner(this.env.config.bannerRoute).then((bannerHTML) => {
            this.state.bannerHTML = bannerHTML;
        } )
    }

    async loadBanner(bannerRoute) {
        let response = await this.rpc(bannerRoute, { context: this.user.context }, { silent: true });
        if (response.code === 503) {
            // Sent by Onboarding Controller when rare concurrent `create` transactions occur
            response = await this.rpc(bannerRoute, { context: this.user.context }, { silent: true });
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

OnboardingBanner.template = xml`<div t-if="transition.shouldMount" t-attf-class="o_onboarding_container w-100 {{transition.className}}" t-ref="onboardingContainer" t-on-click="handleActionLinks" t-out="state.bannerHTML"/>`;
OnboardingBanner.props = {};
