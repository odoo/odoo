/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            fetchMessagesParams
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Object
        [Field/compute]
            {if}
                @record
                .{Thread/model}
                .{=}
                    mail.box
            .{then}
                {Record/insert}
                    [Record/models]
                        Object
            .{elif}
                @record
                .{Thread/model}
                .{=}
                    mail.channel
            .{then}
                {Record/insert}
                    [Record/models]
                        Object
                    [channel_id]
                        @record
                        .{Thread/id}
            .{else}
                {Record/insert}
                    [Record/models]
                        Object
                    [thread_id]
                        @record
                        .{Thread/id}
                    [thread_model]
                        @record
                        .{Thread/model}
`;
