/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            DiscussSidebarCategoryItem
        [Model/fields]
            avatarUrl
            category
            categoryCounterContribution
            channel
            channelType
            counter
            hasLeaveCommand
            hasSettingsCommand
            hasThreadIcon
            hasUnpinCommand
            isActive
            isUnread
        [Model/id]
            DiscussSidebarCategoryItem/category
            .{&}
                DiscussSidebarCategoryItem/channel
        [Model/actions]
            DiscussSidebarCategoryItem/_askAdminConfirmation
            DiscussSidebarCategoryItem/_askLeaveGroupConfirmation
            DiscussSidebarCategoryItem/onClick
            DiscussSidebarCategoryItem/onClickCommandLeave
            DiscussSidebarCategoryItem/onClickCommandSettings
            DiscussSidebarCategoryItem/onClickCommandUnpin
`;
