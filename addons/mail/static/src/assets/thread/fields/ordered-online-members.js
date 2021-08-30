/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        All online members ordered like they are displayed.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            orderedOnlineMembers
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            Partner
        [Field/compute]
            {Thread/_sortMembers}
                [0]
                    @record
                [1]
                    @record
                    .{Thread/members}
                    .{Collection/filter}
                        {Record/insert}
                            [Record/models]
                                Function
                            [Function/in]
                                item
                            [Function/out]
                                @item
                                .{Partner/isOnline}
`;
