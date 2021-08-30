/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            followerSubtypeList
        [Field/model]
            Dialog
        [Field/type]
            one
        [Field/target]
            FollowerSubtypeList
        [Field/isCausal]
            true
        [Field/inverse]
            FollowerSubtypeList/dialogOwner
        [Field/compute]
            {if}
                @record
                .{Dialog/followerOwnerAsSubtypeList}
            .{then}
                {Record/insert}
                    [Record/models]
                        FollowerSubtypeList
            .{else}
                {Record/empty}
`;
