/** @odoo-module **/

import { addFields } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

// ensure that the model definition is loaded before the patch
import '@mail/models/partner';

addFields('Partner', {
    /**
     * States the specific name of this partner in the context of livechat.
     * Either a string or undefined.
     */
    user_livechat_username: attr(),
});
