/**@odoo-module */

import { loadAssets } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
import { useActionLinks } from "@web/views/helpers/view_hook";

export class OnboardingBanner extends owl.Component {
    setup() {
        this.rpc = useService("rpc");
        this.user = useService("user");
        const resModel = "searchModel" in this.env ? this.env.searchModel.resModel : undefined;
        useActionLinks({
            resModel,
            reload: async () => {
                this.bannerHTML = await this.loadBanner(this.env.config.bannerRoute);
                this.render();
            },
        });
    }

    async willStart() {
        this.bannerHTML = await this.loadBanner(this.env.config.bannerRoute);
    }

    async loadBanner(bannerRoute) {
        const response = await this.rpc(bannerRoute, { context: this.user.context });
        if (!response.html) {
            return;
        }

        const banner = new DOMParser().parseFromString(response.html, "text/html");
        const assets = {
            jsLibs: [],
            cssLibs: [],
        };
        banner
            .querySelectorAll(`link[rel="stylesheet"] , script[type="text/javascript"]`)
            .forEach((elem) => {
                if (elem.tagName === "SCRIPT") {
                    assets.jsLibs.push(elem.src);
                } else if (elem.tagName === "LINK") {
                    assets.cssLibs.push(elem.href);
                }
                elem.remove();
            });
        await loadAssets(assets);
        return new XMLSerializer().serializeToString(banner);
    }
}

OnboardingBanner.template = owl.tags.xml`<div class="w-100" t-raw="bannerHTML" />`;
OnboardingBanner.props = {};
