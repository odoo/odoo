/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isDisabled
        [Field/model]
            Chatter
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
        [Field/compute]
            @record
            .{Chatter/thread}
            .{isFalsy}
            .{|}
                @record
                .{Chatter/thread}
                .{Thread/isTemporary}
`;
