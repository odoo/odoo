/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            followerOwnerAsSubtypeList
        [Field/model]
            Dialog
        [Field/type]
            one
        [Field/target]
            Follower
        [Field/inverse]
            Follower/followerSubtypeListDialog
        [Field/isReadonly]
            true
`;
