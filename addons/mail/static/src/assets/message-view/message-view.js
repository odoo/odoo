/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            MessageView
        [Model/fields]
            attachmentList
            component
            composerForEditing
            composerViewInEditing
            deleteMessageConfirmViewOwner
            doHighlight
            extraClass
            highlightTimeout
            isHighlighted
            isSquashed
            message
            messageActionList
            messageInReplyToView
            threadView
        [Model/id]
            MessageView/message
            .{&}
                MessageView/threadView
                .{|}
                    MessageView/deleteMessageConfirmViewOwner
        [Model/actions]
            MessageView/highlight
            MessageView/onClickFailure
            MessageView/onComponentUpdate
            MessageView/replyTo
            MessageView/startEditing
            MessageView/stopEditing
`;
