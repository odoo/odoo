/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether this description can be changed.
        Only makes sense for channels.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isChannelDescriptionChangeable
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
                    channel
                    group
                .{Collection/includes}
                    @record
                    .{Thread/channelType}
`;
