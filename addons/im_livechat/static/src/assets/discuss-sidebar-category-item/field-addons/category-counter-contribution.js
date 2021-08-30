/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            FieldAddon
        [FieldAddon/field]
            DiscussSidebarCategoryItem/categoryCounterContribution
        [FieldAddon/feature]
            im_livechat
        [FieldAddon/compute]
            {switch}
                @record
                .{DiscussSidebarCategoryItem/channel}
                .{Thread/channelType}
            .{case}
                [livechat]
                    {if}
                        @record
                        .{DiscussSidebarCategoryItem/channel}
                        .{Thread/localMessageUnreadCounter}
                        .{>}
                            0
                    .{then}
                        1
                    .{else}
                        0
                []
                    @original
`;
