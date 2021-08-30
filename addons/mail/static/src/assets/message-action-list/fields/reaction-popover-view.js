/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the reaction popover that is active on this message action list.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            reactionPopoverView
        [Field/model]
            MessageActionList
        [Field/type]
            one
        [Field/target]
            PopoverView
        [Field/isCausal]
            true
        [Field/inverse]
            PopoverView/messageActionListOwnerAsReaction
`;
