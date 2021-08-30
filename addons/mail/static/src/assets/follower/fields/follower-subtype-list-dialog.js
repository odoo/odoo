/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            followerSubtypeListDialog
        [Field/model]
            Follower
        [Field/type]
            one
        [Field/target]
            Dialog
        [Field/isCausal]
            true
        [Field/inverse]
            Dialog/followerOwnerAsSubtypeList
`;
