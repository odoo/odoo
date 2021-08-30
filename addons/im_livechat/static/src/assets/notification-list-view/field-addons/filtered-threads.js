/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            FieldAddon
        [FieldAddon/field]
            NotificationListView/filteredThreads
        [FieldAddon/feature]
            im_livechat
        [FieldAddon/compute]
            {if}
                @record
                .{NotificationListView/filter}
                .{=}
                    livechat
            .{then}
                {Record/all}
                    [Record/models]
                        Thread
                    [Thread/channelType]
                        livechat
                    [Thread/isPinned]
                        true
                    [Thread/model]
                        mail.channel
            .{else}
                @original
`;
