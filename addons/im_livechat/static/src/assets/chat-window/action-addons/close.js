/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ActionAddon
        [ActionAddon/action]
            ChatWindow/close
        [ActionAddon/feature]
            im_livechat
        [ActionAddon/params]
            [0]
                chatWindow
            [1]
                notifyServer
        [ActionAddon/behavior]
            {if}
                @chatWindow
                .{ChatWindow/thread}
                .{&}
                    @chatWindow
                    .{ChatWindow/thread}
                    .{Thread/model}
                    .{=}
                        mail.channel
                .{&}
                    @chatWindow
                    .{ChatWindow/thread}
                    .{Thread/channelType}
                    .{=}
                        livechat
                .{&}
                    @chatWindow
                    .{ChatWindow/thread}
                    .{Thread/cache}
                    .{ThreadCache/isLoaded}
                .{&}
                    @chatWindow
                    .{ChatWindow/thread}
                    .{Thread/messages}
                    .{Collection/length}
                    .{=}
                        0
            .{then}
                {Dev/comment}
                    AKU TODO: overwrite param to pass to original
                :notifyServer
                    true
                {Thread/unpin}
                    @chatWindow
                    .{ChatWindow/thread}
            @original
`;
