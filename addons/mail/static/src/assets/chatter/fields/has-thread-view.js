/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether 'this.thread' should be displayed.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasThreadView
        [Field/model]
            Chatter
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{Chatter/thread}
            .{&}
                @record
                .{Chatter/hasMessageList}
`;
