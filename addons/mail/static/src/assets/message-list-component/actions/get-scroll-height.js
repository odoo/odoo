/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessageListComponent/getScrollHeight
        [Action/params]
            record
                [type]
                    MessageListComponent
        [Action/returns]
            Integer
        [Action/behavior]
            {MessageListComponent/_getScrollableElement}
                @record
            .{web.Element/scrollHeight}
`;
