/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/call_demo_view';

registerPatch({
    name: 'CallDemoView',
    fields: {
        /**
         * States the welcome view containing this media preview.
         */
        welcomeView: one('WelcomeView', {
            identifying: true,
            inverse: 'callDemoView',
        }),
    },
});
