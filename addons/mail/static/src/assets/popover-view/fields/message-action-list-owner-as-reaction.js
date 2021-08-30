/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        If set, this popover view is owned by a message action list.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messageActionListOwnerAsReaction
        [Field/model]
            PopoverView
        [Field/type]
            one
        [Field/target]
            MessageActionList
        [Field/isReadonly]
            true
        [Field/inverse]
            MessageActionList/reactionPopoverView
`;
