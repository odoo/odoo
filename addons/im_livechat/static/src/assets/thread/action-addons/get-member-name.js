/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ActionAddon
        [ActionAddon/action]
            Thread/getMemberName
        [ActionAddon/feature]
            im_livechat
        [ActionAddon/behavior]
            {if}
                @record
                .{Thread/channelType}
                .{=}
                    livechat
                .{&}
                    @partner
                    .{Partner/livechatUsername}
            .{then}
                @partner
                .{Partner/livechatUsername}
            .{else}
                @original
`;
