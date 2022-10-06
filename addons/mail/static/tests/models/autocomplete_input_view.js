/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

registerPatch({
    name: 'AutocompleteInputView',
    recordMethods: {
        onSource(req, res) {
            this._super(req, res);
            this.messaging.messagingBus.trigger('o-AutocompleteInput-source');
        },
    },
});
