/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the message action list of this message view (if any).
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messageActionList
        [Field/model]
            MessageView
        [Field/type]
            one
        [Field/target]
            MessageActionList
        [Field/isCausal]
            true
        [Field/isReadonly]
            true
        [Field/inverse]
            MessageActionList/messageView
        [Field/compute]
            {if}
                @record
                .{MessageView/deleteMessageConfirmViewOwner}
            .{then}
                {Record/empty}
            .{else}
                {Record/insert}
                    [Record/models]
                        MessageActionList
`;
