/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isFromCurrentUser
        [Field/model]
            Notification
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            {if}
                {Env/currentPartner}
                .{isFalsy}
                .{|}
                    @record
                    .{Notification/message}
                    .{isFalsy}
                .{|}
                    @record
                    .{Notification/message}
                    .{Message/author}
                    .{isFalsy}
            .{then}
                {Record/empty}
            .{else}
                {Env/currentPartner}
                .{=}
                    @record
                    .{Notification/message}
                    .{Message/author}
`;
