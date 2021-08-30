/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messagingMenuAsPinnedAndUnreadChannel
        [Field/model]
            Thread
        [Field/type]
            one
        [Field/target]
            MessagingMenu
        [Field/isReadonly]
            true
        [Field/inverse]
            MessagingMenu/pinnedAndUnreadChannels
        [Field/compute]
            {if}
                @record
                .{Thread/model}
                .{=}
                    mail.channel
                .{&}
                    @record
                    .{Thread/isPinned}
                .{&}
                    @record
                    .{Thread/localMessageUnreadCounter}
                    .{>}
                        0
            .{then}
                {Env/messagingMenu}
            .{else}
                {Record/empty}
`;
