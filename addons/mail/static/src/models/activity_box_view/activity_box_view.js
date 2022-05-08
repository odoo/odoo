/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';

registerModel({
    name: 'mail.activity_box_view',
    identifyingFields: ['chatter'],
    lifecycleHooks: {
        _created() {
            // Bind necessary until OWL supports arrow function in handlers: https://github.com/odoo/owl/issues/876
            this.onClickActivityBoxTitle = this.onClickActivityBoxTitle.bind(this);
        },
    },
    recordMethods: {
        /**
         * Handles click on activity box title.
         */
        onClickActivityBoxTitle(ev) {
            ev.preventDefault();
            this.update({ isActivityListVisible: !this.isActivityListVisible });
        },
    },
    fields: {
        chatter: one2one('mail.chatter', {
            inverse: 'activityBoxView',
            readonly: true,
            required: true,
        }),
        isActivityListVisible: attr({
            default: true,
        }),
    },  

});
