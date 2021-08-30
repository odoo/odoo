/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageListComponent/_getScrollableElement
        [Action/params]
            record
                [type]
                    MessageListComponent
        [Action/returns]
            Element
                [description]
                    Scrollable element
        [Action/behavior]
            @record
            .{MessageListComponent/getScrollableElement}
            .{|}
                @record
                .{MessageListComponent/root}
`;
