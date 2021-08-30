/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Tell whether the message is selected in the current thread viewer.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isSelected
        [Field/model]
            MessageViewComponent
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{MessageViewComponent/threadView}
            .{&}
                @record
                .{MessageViewComponent/threadView}
                .{ThreadView/threadViewer}
                .{ThreadViewer/replyingToMessageView}
                .{=}
                    @record
                    .{MessageViewComponent/messageView}
`;
