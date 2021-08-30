/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Display the previous attachment in the list of attachments.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentViewerComponent/_previous
        [Action/params]
            record
        [Action/behavior]
            {AttachmentList/selectPreviousAttachment}
                @record
                .{AttachmentViewerComponent/attachmentViewer}
                .{AttachmentViewer/dialogOwner}
                .{Dialog/attachmentListOwnerAsAttachmentView}
`;
