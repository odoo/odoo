/** @odoo-module **/

import options from 'web_editor.snippets.options';

options.registry.WebsiteEvent = options.Class.extend({

    /**
     * @override
     */
    async start() {
        const res = await this._super(...arguments);
        const eventObject = this._getEventObject();
        this.modelName = eventObject.model;
        this.eventId = eventObject.id;
        // Only need for one RPC request as the option will be destroyed if a
        // change is made.
        const rpcData = await this._rpc({
            model: this.modelName,
            method: 'read',
            args: [
                [this.eventId],
                ['website_menu', 'website_url'],
            ],
        });
        this.eventUrl = rpcData[0]['website_url'];
        this.data.reload = this.eventUrl;
        this.websiteMenu = rpcData[0]['website_menu'];
        return res;
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    displaySubmenu(previewMode, widgetValue, params) {
        return this._rpc({
            model: this.modelName,
            method: 'toggle_website_menu',
            args: [[this.eventId], widgetValue],
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'displaySubmenu': {
                return this.websiteMenu;
            }
        }
        return this._super(...arguments);
    },
    /**
     * @private
     */
    _getEventObject() {
        const repr = this.ownerDocument.documentElement.dataset.mainObject;
        const m = repr.match(/(.+)\((\d+),(.*)\)/);
        return {
            model: m[1],
            id: m[2] | 0,
        };
    },
});
