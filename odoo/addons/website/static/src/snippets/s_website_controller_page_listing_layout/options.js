/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";

const mainObjectRe = /website\.controller\.page\(((\d+,?)*)\)/;

options.registry.WebsiteControllerPageListingLayout = options.Class.extend({
    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
        this.orm = this.bindService("orm");
        this.resModel = "website.controller.page";
    },

    /**
     * @override
     */
    async willStart() {
        const _super = this._super.bind(this);
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
        return _super(...arguments);
    },

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
            this.rpc("/website/save_session_layout_mode", params),
        ]);
    },

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
   },
});
