/** @odoo-module **/

import options from 'web_editor.snippets.options';

options.registry.WebsiteEvent.include({
    rpcFields: options.registry.WebsiteEvent.prototype.rpcFields.concat(['meeting_room_allow_creation']),

    async start() {
        await this._super(...arguments);
        this.meetingRoomAllowCreation = this.rpcData[0]['meeting_room_allow_creation'];
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    allowRoomCreation(previewMode, widgetValue, params) {
        return this._rpc({
            model: this.modelName,
            method: 'write',
            args: [[this.eventId], {
                meeting_room_allow_creation: widgetValue
            }],
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'allowRoomCreation': {
                return this.meetingRoomAllowCreation;
            }
        }
        return this._super(...arguments);
    },
});
