/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            attachmentBackLinkText
        [Element/model]
            MessageInReplyToViewComponent
        [Element/isPresent]
            @record
            .{MessageInReplyToViewComponent/messageInReplyToView}
            .{MessageInReplyToView/hasAttachmentBackLink}
        [web.Element/tag]
            span
        [web.Element/class]
            font-italic
            mr-2
        [web.Element/textContent]
            {Locale/text}
                Click to see the attachments
`;
