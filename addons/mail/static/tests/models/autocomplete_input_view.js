/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/models/autocomplete_input_view';

patchRecordMethods('AutocompleteInputView', {
    onSource(req, res) {
        this._super(req, res);
        this.messaging.messagingBus.trigger('o-AutocompleteInput-source');
    },
});
