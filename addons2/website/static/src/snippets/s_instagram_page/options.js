/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";
import options from "@web_editor/js/editor/snippets.options";
import SocialMediaOption from "@website/snippets/s_social_media/options";

options.registry.InstagramPage = options.Class.extend({
    /**
     * @override
     */
    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
        this.notification = this.bindService("notification");
        this.instagramUrlStr = "instagram.com/";
    },
    /**
     * @override
     */
    async onBuilt() {
        // First we check if the user has changed his instagram during the
        // current edition (via the social media options).
        const dbSocialValuesCache = SocialMediaOption.getDbSocialValuesCache();
        let socialInstagram = dbSocialValuesCache && dbSocialValuesCache["social_instagram"];
        // If not, we check the value in the DB.
        if (!socialInstagram) {
            let websiteId;
            this.trigger_up("context_get", {
                callback: function (ctx) {
                    websiteId = ctx["website_id"];
                },
            });
            const values = await this.orm.read("website", [websiteId], ["social_instagram"]);
            socialInstagram = values[0]["social_instagram"];
        }
        if (socialInstagram) {
            const pageName = this._getInstagramPageNameFromUrl(socialInstagram);
            if (pageName) {
                this.$target[0].dataset.instagramPage = pageName;
            }
        }
    },

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
        await this.trigger_up("widgets_start_request", {
            $target: this.$target,
            editableMode: true,
        });
    },

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
        return this._super(...arguments);
    },
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
    },
});

export default {
    InstagramPage: options.registry.InstagramPage,
};
