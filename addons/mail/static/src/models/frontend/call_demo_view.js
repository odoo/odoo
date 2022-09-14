/** @odoo-module **/

import { addFields } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/call_demo_view';

addFields('CallDemoView', {
    /**
     * States the welcome view containing this media preview.
     */
     welcomeView: one('WelcomeView', {
        identifying: true,
        inverse: 'callDemoView',
    }),
});
