/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            body
        [Element/model]
            MessageInReplyToViewComponent
        [Element/isPresent]
            @record
            .{MessageInReplyToViewComponent/messageInReplyToView}
            .{MessageInReplyToView/messageView}
            .{MessageView/message}
            .{Message/parentMessage}
            .{Message/isEmpty}
            .{isFalsy}
        [web.Element/tag]
            span
        [web.Element/class]
            ml-1
        [Element/onClick]
            {MessageInReplyToView/onClick}
                [0]
                    @record
                    .{MessageInReplyToViewComponent/messageInReplyToView}
                [1]
                    @ev
        [web.Element/style]
            [web.scss/cursor]
                pointer
            {scss/include}
                {scss/o-hover-text-color}
                    {scss/$o-main-color-muted}
                    inherit
            {web.scss/selector}
                {Dev/comment}
                    Make the body single line when possible
                [0]
                    p, div
                [1]
                    [web.scss/display]
                        inline
                    [web.scss/margin]
                        0
            {web.scss/selector}
                [0]
                    br
                [1]
                    [web.scss/display]
                        none
`;
