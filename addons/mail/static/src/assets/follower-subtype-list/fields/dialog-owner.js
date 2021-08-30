/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the dialog displaying this follower subtype list.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            dialogOwner
        [Field/model]
            FollowerSubtypeList
        [Field/type]
            one
        [Field/target]
            Dialog
        [Field/isCausal]
            true
        [Field/isReadonly]
            true
        [Field/inverse]
            Dialog/followerSubtypeList
`;
