/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            notificationNonFailurePopover
        [Element/model]
            MessageViewComponent
        [Field/target]
            NotificationPopoverComponent
        [NotificationPopoverComponent/messageview]
            @record
            .{MessageViewComponent/messageView}
`;
