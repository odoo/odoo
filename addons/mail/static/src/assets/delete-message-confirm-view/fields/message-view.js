/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the message view that this delete message confirm view
        will use to display this message.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messageView
        [Field/model]
            DeleteMessageConfirmView
        [Field/type]
            one
        [Field/target]
            MessageView
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
        [Field/isCausal]
            true
        [Field/inverse]
            MessageView/deleteMessageConfirmViewOwner
        [Field/compute]
            {if}
                @record
                .{DeleteMessageConfirmView/message}
            .{then}
                {Record/insert}
                    [Record/models]
                        MessageView
                    [MessageView/message]
                        @record
                        .{DeleteMessageConfirmView/message}
            .{else}
                {Record/empty}
`;
