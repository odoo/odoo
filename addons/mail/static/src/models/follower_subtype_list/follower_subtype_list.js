/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { many2one } from '@mail/model/model_field';

function factory(dependencies) {

    class FollowerSubtypeList extends dependencies['mail.model'] {}

    FollowerSubtypeList.fields = {
        follower: many2one('mail.follower'),
    };

    FollowerSubtypeList.modelName = 'mail.follower_subtype_list';

    return FollowerSubtypeList;
}

registerNewModel('mail.follower_subtype_list', factory);
