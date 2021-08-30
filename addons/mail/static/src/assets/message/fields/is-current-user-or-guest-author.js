/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isCurrentUserOrGuestAuthor
        [Field/model]
            Message
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
        [Field/compute]
            @record
            .{Message/author}
            .{&}
                {Env/currentPartner}
            .{&}
                {Env/currentPartner}
                .{=}
                    @record
                    .{Message/author}
            .{|}
                @record
                .{Message/guestAuthor}
                .{&}
                    @record
                    .{Message/currentGuest}
                .{&}
                    {Env/currentGuest}
                    .{=}
                        @record
                        .{Message/guestAuthor}
`;
