/** @odoo-module **/

import options from 'web_editor.snippets.options';

options.registry.WebsiteEvent = options.Class.extend({

    /**
     * @override
     */
    async start() {
        const res = await this._super(...arguments);
        this.currentWebsiteUrl = this.ownerDocument.location.pathname;
        this.eventId = this._getEventObjectId();
        // Only need for one RPC request as the option will be destroyed if a
        // change is made.
        const rpcData = await this._rpc({
            model: 'event.event',
            method: 'read',
            args: [
                [this.eventId],
                ['website_menu'],
            ],
        });
        this.data.reload = this.currentWebsiteUrl;
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
            model: 'event.event',
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
     * Ensure that we get the event object id as we could be inside a sub-object of the event
     * like an event.track
     * @private
     */
    _getEventObjectId() {
        const objectIds = this.currentWebsiteUrl.match(/(?<=-)\d+(?![-\w\d])/);
        return parseInt(objectIds[0]) | 0;
    },
});
