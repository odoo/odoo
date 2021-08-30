/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ActionAddon
        [ActionAddon/action]
            MessagingNotificationHandler/_handleNotificationResUsersSettings
        [ActionAddon/feature]
            im_livechat
        [ActionAddon/params]
            record
            settings
        [ActionAddon/behavior]
            {if}
                @settings
                .{Dict/hasKey}
                    is_discuss_sidebar_category_livechat_open
            .{then}
                {Record/update}
                    [0]
                        {Discuss/categoryLivechat}
                    [1]
                        [DiscussSidebarCategory/isServerOpen]
                            @settings
                            .{Dict/get}
                                is_discuss_sidebar_category_livechat_open
            @original
`;
