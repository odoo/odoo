/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import options from "@web_editor/js/editor/snippets.options";

const widgetRegistry = options.userValueWidgetsRegistry;

widgetRegistry["we-many2one-marketing-card"] = widgetRegistry["we-many2one"].extend({
    init(parent, title, options, $target) {
        this.record = parent.options.record;
        return this._super(...arguments);
    },
    async _getSearchDomain() {
        const domain = await this._super(...arguments);
        const mailingModel = this.record?.data?.mailing_model_real;
        return mailingModel ? domain.concat([["res_model", "=", mailingModel]]) : domain;
    },
});

options.registry.MarketingCard = options.Class.extend({
    setCardsCampaign(previewMode, widgetValue, params) {
        const widgetEl = this.$target[0];
        const anchorEl = widgetEl.querySelector("a");
        const imageEl = widgetEl.querySelector("img");
        widgetEl.dataset.campaignId = widgetValue;
        anchorEl.href = `/cards/${widgetValue}/preview`;
        if (imageEl) {
            imageEl.src = `/web/image/card.campaign/${widgetValue}/image_preview`;
        }
    },
    setDisplayCard(previewMode, widgetValue, params) {
        const widgetEl = this.$target[0];
        const anchorEl = widgetEl.querySelector("a");
        if (widgetValue == "link") {
            anchorEl.text = anchorEl.text?.trim() || _t("Your Card");
            const imageEl = widgetEl.querySelector("img");
            if (imageEl) {
                imageEl.remove();
            }
        } else {
            widgetEl.dataset.anchorText = anchorEl.text;
            anchorEl.text = "";
            const campaignId = widgetEl.dataset.campaignId || 0;
            const imageEl = document.createElement("img");
            imageEl.setAttribute("src", `/web/image/card.campaign/${campaignId}/image_preview`);
            imageEl.setAttribute("alt", "Card Preview");
            imageEl.setAttribute("class", "img-fluid border border-3");
            anchorEl.appendChild(imageEl);
        }
    },
    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        switch (methodName) {
            case "setCardsCampaign": {
                return this.$target[0].dataset.campaignId;
            }
            case "setDisplayCard": {
                return this.$target[0].querySelector("img") ? "card" : "link";
            }
        }
        return this._super(...arguments);
    },
});
