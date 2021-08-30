/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasUserReacted
        [Field/model]
            MessageReactionGroup
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
        [Field/compute]
            {Env/currentPartner}
            .{&}
                @record
                .{MessageReactionGroup/partners}
                .{Collection/includes}
                    {Env/currentPartner}
            .{|}
                {Env/currentGuest}
                .{&}
                    @record
                    .{MessageReactionGroup/guests}
                    .{Collection/includes}
                        {Env/currentGuest}
`;
