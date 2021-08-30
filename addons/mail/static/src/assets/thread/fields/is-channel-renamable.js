/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether this thread can be renamed.
        Only makes sense for channels.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isChannelRenamable
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{Thread/model}
            .{=}
                mail.channel
            .{&}
                {Record/insert}
                    [Record/models]
                        Collection
                    chat
                    channel
                    group
                .{Collection/includes}
                    @record
                    .{Thread/channelType}
`;
