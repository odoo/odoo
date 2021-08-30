/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Context
        [Context/name]
            follower
        [Context/model]
            FollowerListMenuComponent
        [Model/fields]
            follower
        [Model/template]
            followerForeach
                follower
`;
