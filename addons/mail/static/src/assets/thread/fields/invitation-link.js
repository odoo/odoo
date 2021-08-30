/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            invitationLink
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{Thread/uuid}
                .{isFalsy}
                .{|}
                    @record
                    .{Thread/channelType}
                    .{isFalsy}
                .{|}
                    @record
                    .{Thread/channelType}
                    .{=}
                        chat
            .{then}
                {Record/empty}
            .{else}
                {web.Browser/location}
                .{Dict/get}
                    origin
                .{+}
                    /chat/
                .{+}
                    @record
                    .{Thread/id}
                .{+}
                    /
                .{+}
                    @record
                    .{Thread/uuid}
`;
