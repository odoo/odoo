/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Display the previous attachment in the list of attachments.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentViewerComponent/_next
        [Action/params]
            record
        [Action/behavior]
            {AttachmentList/selectNextAttachment}
                @record
                .{AttachmentViewerComponent/attachmentViewer}
                .{AttachmentViewer/dialogOwner}
                .{Dialog/attachmentListOwnerAsAttachmentView}
`;
