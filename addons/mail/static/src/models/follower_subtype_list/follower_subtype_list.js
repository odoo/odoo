/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { many2one } from '@mail/model/model_field';

function factory(dependencies) {

    class FollowerSubtypeList extends dependencies['mail.model'] {

        /**
         * Called when clicking on close button.
         */
        onClickCancel() {
            this.follower.closeSubtypes();
        }

        /**
         * Called when clicking on close button.
         */
        onClickClose() {
            this.follower.closeSubtypes();
        }

        /**
         * Called when clicking on apply button.
         */
        onClickApply() {
            this.follower.updateSubtypes();
        }

    }

    FollowerSubtypeList.fields = {
        follower: many2one('mail.follower'),
    };

    FollowerSubtypeList.modelName = 'mail.follower_subtype_list';

    return FollowerSubtypeList;
}

registerNewModel('mail.follower_subtype_list', factory);
