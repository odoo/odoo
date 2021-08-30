/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DiscussSidebarCategoryItem/onClickCommandLeave
        [Action/params]
            ev
                [type]
                    web.MouseEvent
            record
                [type]
                    DiscussSidebarCategoryItem
        [Action/behavior]
            {web.Event/stopPropagation}
                @ev
            {if}
                @record
                .{DiscussSidebarCategoryItem/channel}
                .{Thread/channelType}
                .{!=}
                    group
                .{&}
                    @record
                    .{DiscussSidebarCategoryItem/channel}
                    .{Thread/creator}
                    .{=}
                        {Env/currentUser}
            .{then}
                {DiscussSidebarCategoryItem/_askAdminConfirmation}
                    @record
            {if}
                @record
                .{DiscussSidebarCategoryItem/channel}
                .{Thread/channelType}
                .{=}
                    group
            .{then}
                {DiscussSidebarCategoryItem/_askLeaveGroupConfirmation}
                    @record
            {Thread/unsubscribe}
                @record
                .{DiscussSidebarCategoryItem/channel}
`;
