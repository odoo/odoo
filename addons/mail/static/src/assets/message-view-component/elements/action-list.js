/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            actionList
        [Element/model]
            MessageViewComponent
        [Field/target]
            MessageActionListComponent
        [MessageActionListComponent/messageActionList]
            @record
            .{MessageViewComponent/messageView}
            .{MessageView/messageActionList}
`;
