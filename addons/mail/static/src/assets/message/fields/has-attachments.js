/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
       States whether the message has some attachments.
    {Record/insert}
       [Record/models]
           Field
        [Field/name]
            hasAttachments
        [Field/model]
            Message
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{Message/attachments}
            .{Collection/length}
            .{>}
                0
`;
