/** @odoo-module **/

import options from 'web_editor.snippets.options';

options.registry.WebsiteEvent.include({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    allowRoomCreation(previewMode, widgetValue, params) {
        this._rpc({
            model: this.modelName,
            method: 'write',
            args: [[this.eventId], {
                meeting_room_allow_creation: widgetValue
            }],
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
                return this._getRpcData('meeting_room_allow_creation');
            }
        }
        return this._super(...arguments);
    },
});
