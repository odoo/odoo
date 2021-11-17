/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';
import { clear, link } from '@mail/model/model_field_command';

function factory(dependencies) {

    class ActivityBoxView extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            // Bind necessary until OWL supports arrow function in handlers: https://github.com/odoo/owl/issues/876
            this.onClickActivityBoxTitle = this.onClickActivityBoxTitle.bind(this);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Handles click on activity box title.
         */
        onClickActivityBoxTitle() {
            this.update({ isActivityListVisible: !this.isActivityListVisible });
        }

    }

    ActivityBoxView.fields = {
        chatter: one2one('mail.chatter', {
            inverse: 'activityBoxView',
            readonly: true,
            required: true,
        }),
        isActivityListVisible: attr({
            default: true,
        }),
    };
    ActivityBoxView.identifyingFields = ['chatter'];
    ActivityBoxView.modelName = 'mail.activity_box_view';

    return ActivityBoxView;
}

registerNewModel('mail.activity_box_view', factory);
