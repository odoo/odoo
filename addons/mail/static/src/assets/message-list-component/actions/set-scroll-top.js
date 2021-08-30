/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageListComponent/setScrollTop
        [Action/params]
            record
                [type]
                    MessageListComponent
            value
                [type]
                    Integer
        [Action/behavior]
            {if}
                {MessageListComponent/_getScrollableElement}
                    @record
                .{web.Element/scrollTop}
                .{=}
                    @value
            .{then}
                {break}
            {Record/update}
                [0]
                    @record
                    .{MessageListComponent/messageListView}
                [1]
                    [MessageListView/isLastScrollProgrammatic]
                        true
            {Record/update}
                [0]
                    {MessageListComponent/_getScrollableElement}
                        @record
                [1]
                    [web.Element/scrollTop]
                        @value
`;
