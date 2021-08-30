/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether this chat window has the invite feature.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasInviteFeature
        [Field/model]
            ChatWindow
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{ChatWindow/thread}
            .{&}
                @record
                .{ChatWindow/thread}
                .{Thread/hasInviteFeature}
            .{&}
                {Device/isMobile}
`;
