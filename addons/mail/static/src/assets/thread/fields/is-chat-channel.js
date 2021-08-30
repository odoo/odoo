/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether this thread is a 'mail.channel' qualified as chat.

        Useful to list chat channels, like in messaging menu with the filter
        'chat'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isChatChannel
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
        [Field/compute]
            @record
            .{Thread/channelType}
            .{=}
                chat
            .{|}
                @record
                .{Thread/channelType}
                .{=}
                    group
`;
