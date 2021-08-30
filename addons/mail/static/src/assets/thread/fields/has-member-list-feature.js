/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether it makes sense for this thread to have a member list.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasMemberListFeature
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
