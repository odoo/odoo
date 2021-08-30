/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Close the dialog with this attachment viewer.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentViewerComponent/_close
        [Action/params]
            record
        [Action/behavior]
            {Record/delete}
                @record
                .{AttachmentViewerComponent/record}
`;
