/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            MessageInReplyToView
        [Model/fields]
            hasAttachmentBackLink
            hasBodyBackLink
            messageView
        [Model/id]
            MessageInReplyToView/messageView
        [Model/actions]
            MessageInReplyToView/onClickReply
`;
