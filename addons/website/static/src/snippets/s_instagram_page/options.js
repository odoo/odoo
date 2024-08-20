/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";
import { SnippetOption } from "@web_editor/js/editor/snippets.options";
import { registerWebsiteOption } from "@website/js/editor/snippets.registry";
import SocialMediaOption from "@website/snippets/s_social_media/options";

export class InstagramPage extends SnippetOption {

    constructor() {
        super(...arguments);
        this.orm = this.env.services.orm;
        this.notification = this.env.services.notification;
        this.website = this.env.services.website;
        this.instagramUrlStr = "instagram.com/";
    }
    /**
     * @override
     */
    async onBuilt() {
        // First we check if the user has changed his instagram during the
        // current edition (via the social media options).
        const dbSocialValuesCache = SocialMediaOption.getDbSocialValuesCache().dbSocialValues;
        let socialInstagram = dbSocialValuesCache && dbSocialValuesCache["social_instagram"];
        // If not, we check the value in the DB.
        if (!socialInstagram) {
            const values = await this.orm.read("website", [this.website.currentWebsite.id], ["social_instagram"]);
            socialInstagram = values[0]["social_instagram"];
        }
        if (socialInstagram) {
            const pageName = this._getInstagramPageNameFromUrl(socialInstagram);
            if (pageName) {
                this.$target[0].dataset.instagramPage = pageName;
            }
        }
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Registers the instagram page name.
     *
     * @see this.selectClass for parameters
     */
    async setInstagramPage(previewMode, widgetValue, params) {
        if (widgetValue.includes(this.instagramUrlStr)) {
            widgetValue = this._getInstagramPageNameFromUrl(widgetValue);
        }
        if (!widgetValue) {
            this.notification.add(_t("The Instagram page name is not valid"), {
                type: "warning",
            });
        }
        this.$target[0].dataset.instagramPage = widgetValue || "";
        // As the public widget restart is disabled for instagram, we have to
        // manually restart the widget.
        await new Promise((resolve, reject) => {
            this.website.websiteRootInstance.trigger_up("widgets_start_request", {
                $target: this.$target,
                editableMode: true,
                onSuccess: () => resolve(),
                onFailure: () => reject(),
            });
        });
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(widgetName, params) {
        if (widgetName === "setInstagramPage") {
            return this.$target[0].dataset.instagramPage;
        }
        return super._computeWidgetState(...arguments);
    }
    /**
     * Returns the instagram page name from the given url.
     *
     * @private
     * @param {string} url
     * @returns {string|undefined}
     */
    _getInstagramPageNameFromUrl(url) {
        const pageName = url.split(this.instagramUrlStr)[1];
        if (!pageName || pageName.includes("?") || pageName.includes("#") ||
            (pageName.includes("/") && pageName.split("/")[1].length > 0)) {
            return;
        }
        return pageName.split("/")[0];
    }
}

registerWebsiteOption("InstagramPage", {
    Class: InstagramPage,
    template: "website.s_instagram_page_options",
    selector: ".s_instagram_page",
});
