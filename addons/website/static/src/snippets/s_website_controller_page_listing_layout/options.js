/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import {
    SnippetOption,
} from "@web_editor/js/editor/snippets.options";
import { rpc } from "@web/core/network/rpc";
import {
    registerWebsiteOption,
} from "@website/js/editor/snippets.registry";

const mainObjectRe = /website\.controller\.page\(((\d+,?)*)\)/;

export class WebsiteControllerPageListingLayoutOption extends SnippetOption {

    constructor() {
        super(...arguments);
        this.orm = this.env.services.orm;
        this.resModel = "website.controller.page";
    }

    /**
     * @override
     */
    async willStart() {
        const mainObjectRepr = this.$target[0].ownerDocument.documentElement.getAttribute("data-main-object");
        const match = mainObjectRe.exec(mainObjectRepr);
        if (match && match[1]) {
            this.resIds = match[1].split(",").flatMap(e => {
                if (!e) {
                    return [];
                }
                const id = parseInt(e);
                return id ? [id] : [];
            });
        }

        const results = await this.orm.read(this.resModel, this.resIds, ["default_layout"]);
        this.layout = results[0]["default_layout"];
        return super.willStart(...arguments);
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    async setLayout(previewMode, widgetValue) {
        const params = {
            layout_mode: widgetValue,
            view_id: this.$target[0].getAttribute("data-view-id"),
        };
        // save the default layout display, and set the layout for the current user
        await Promise.all([
            this.orm.write(this.resModel, this.resIds, { default_layout: widgetValue }),
            rpc("/website/save_session_layout_mode", params),
        ]);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
    *
    * @param methodName
    * @param params
    * @returns {string|string|*}
    * @private
    */
   _computeWidgetState(methodName) {
        switch (methodName) {
            case 'setLayout': {
                return this.layout;
            }
        }
        return this._super(...arguments);
   }
}

registerWebsiteOption("WebsiteControllerPageListingLayout", {
    Class: WebsiteControllerPageListingLayoutOption,
    template: "website.s_website_controller_page_listing_layout_option",
    selector: ".listing_layout_switcher",
    noCheck: true,
    data: {
        string: _t("Layout"),
        pageOptions:true,
        groups: ["website.group_website_designer"]
    },
});
