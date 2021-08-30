/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            follower
        [Field/model]
            FollowerSubtypeList
        [Field/type]
            one
        [Field/target]
            Follower
        [Field/isRequired]
            true
        [Field/related]
            Follower/dialogOwner
            Dialog/followerOwnerAsSubtypeList
`;
