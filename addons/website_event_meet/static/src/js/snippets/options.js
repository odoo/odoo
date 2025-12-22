/** @odoo-module **/

import options from '@web_editor/js/editor/snippets.options';

options.registry.WebsiteEvent.include({

    /**
     * @override
     */
    async start() {
        const res = await this._super(...arguments);
        const rpcData = await this.orm.read("event.event", [this.eventId], ["meeting_room_allow_creation"]);
        this.meetingRoomAllowCreation = rpcData[0]['meeting_room_allow_creation'];
        return res;
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    allowRoomCreation(previewMode, widgetValue, params) {
        return this.orm.write("event.event", [this.eventId], {
            meeting_room_allow_creation: widgetValue,
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
