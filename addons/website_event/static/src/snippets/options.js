/** @odoo-module **/

import options from 'web_editor.snippets.options';

options.registry.WebsiteEvent = options.Class.extend({

    /**
     * @override
     */
    start() {
        const eventObject = this._getEventObject();
        this.modelName = eventObject.model;
        this.eventId = eventObject.id;
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    displaySubmenu(previewMode, widgetValue, params) {
        this._rpc({
            model: this.modelName,
            method: 'toggle_website_menu',
            args: [[this.eventId], widgetValue],
        }).then(() => this.trigger_up('reload_editable', {option_selector: this.data.selector}));
        // TODO: if widgetValue is false, it should reload on the event url
        // page ('website_url' field).
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'displaySubmenu': {
                return this._getRpcData('website_menu');
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
    /**
     * @private
     * @param {string}
     * @returns {boolean}
     */
    async _getRpcData(field) {
        const data = await this._rpc({
            model: this.modelName,
            method: 'read',
            args: [
                [this.eventId],
                [field],
            ],
        });
        return data[0][field];
    },
});
