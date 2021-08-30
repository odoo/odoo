/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether the message is highlighted.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isHighlighted
        [Field/model]
            Message
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{Message/isCurrentPartnerMentioned}
            .{&}
                @record
                .{Message/originThread}
            .{&}
                @record
                .{Message/originThread}
                .{Thread/model}
                .{=}
                    mail.channel
`;
