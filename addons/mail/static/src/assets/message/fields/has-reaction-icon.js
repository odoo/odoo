/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether the message has a reaction icon.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasReactionIcon
        [Field/model]
            Message
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{Message/isTemporary}
            .{isFalsy}
            .{&}
                @record
                .{Message/isTransient}
                .{isFalsy}
`;
