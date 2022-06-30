/**@odoo-module */

import { loadCSS, loadJS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
import { useActionLinks } from "@web/views/view_hook";

const { Component, markup, onWillStart, xml } = owl;

export class OnboardingBanner extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.user = useService("user");
        const resModel = "searchModel" in this.env ? this.env.searchModel.resModel : undefined;
        this.handleActionLinks = useActionLinks({
            resModel,
            reload: async () => {
                this.bannerHTML = await this.loadBanner(this.env.config.bannerRoute);
                this.render();
            },
        });

        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        this.bannerHTML = await this.loadBanner(this.env.config.bannerRoute);
    }

    async loadBanner(bannerRoute) {
        const response = await this.rpc(bannerRoute, { context: this.user.context });
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

OnboardingBanner.template = xml`<div class="w-100" t-on-click="handleActionLinks" t-out="bannerHTML"/>`;
OnboardingBanner.props = {};
