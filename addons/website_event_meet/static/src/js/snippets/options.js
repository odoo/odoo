/** @odoo-module **/

import options from 'web_editor.snippets.options';

options.registry.WebsiteEvent.include({

    /**
     * @override
     */
    async start() {
        const res = await this._super(...arguments);
        const rpcData = await this._rpc({
            model: 'event.event',
            method: 'read',
            args: [
                [this.eventId],
                ['meeting_room_allow_creation'],
            ],
        });
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
        return this._rpc({
            model: 'event.event',
            method: 'write',
            args: [[this.eventId], {
                meeting_room_allow_creation: widgetValue
            }],
        // TODO: Remove the request_save in master, it's already done by the
        // data-page-options set to true in the template.
        }).then(() => this.trigger_up('request_save', {reload: true, optionSelector: this.data.selector}));
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
