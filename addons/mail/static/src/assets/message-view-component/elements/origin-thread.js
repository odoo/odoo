/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            originThread
        [Element/model]
            MessageViewComponent
        [Element/isPresent]
            @record
            .{MessageViewComponent/threadView}
            .{&}
                @record
                .{MessageViewComponent/messageView}
                .{MessageView/message}
                .{Message/originThread}
            .{&}
                @record
                .{MessageViewComponent/messageView}
                .{MessageView/message}
                .{Message/originThread}
                .{!=}
                    @record
                    .{MessageViewComponent/threadView}
                    .{ThreadView/thread}
        [web.Element/style]
            [web.scss/margin-inline-end]
                {scss/map-get}
                    {scss/$spacers}
                    2
            [web.scss/font-size]
                0.8em
            [web.scss/color]
                {scss/gray}
                    500
            {if}
                @record
                .{MessageViewComponent/isSelected}
            .{then}
                [web.scss/color]
                    {scss/gray}
                        600
`;
