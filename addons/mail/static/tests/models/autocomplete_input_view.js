/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

registerPatch({
    name: 'AutocompleteInputView',
    recordMethods: {
        async onInputSearch(ev) {
            this._super(ev);
            this.messaging.messagingBus.trigger('o-AutocompleteInput-search');
        },
    },
});
