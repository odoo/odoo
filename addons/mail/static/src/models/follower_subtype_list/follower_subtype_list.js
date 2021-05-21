/** @odoo-module **/

import { many2one } from '@mail/model/model_field';

export function factoryFollowerSubtypeList(dependencies) {

    class FollowerSubtypeList extends dependencies['mail.model'] {}

    FollowerSubtypeList.fields = {
        follower: many2one('mail.follower'),
    };

    return FollowerSubtypeList;
}
