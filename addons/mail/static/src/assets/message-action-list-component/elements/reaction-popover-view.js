/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            reactionPopoverView
        [Field/model]
            MessageActionListComponent
        [Record/models]
            PopoverViewComponent
        [PopoverViewComponent/popoverView]
            @record
            .{MessageActionListComponent/messageActionList}
            .{MessageActionList/reactionPopoverView}
        [Element/isPresent]
            @record
            .{MessageActionListComponent/messageActionList}
            .{MessageActionList/reactionPopoverView}
`;
