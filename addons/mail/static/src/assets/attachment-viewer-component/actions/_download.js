/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Download the attachment.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentViewerComponent/_download
        [Action/params]
            record
        [Action/behavior]
            @env
            .{Env/owlEnv}
            .{Dict/get}
                services
            .{Dict/get}
                navigate
            .{Function/call}
                [0]
                    /web/content/ir.attachment/
                    .{+}
                        @record
                        .{AttachmentViewerComponent/record}
                        .{AttachmentViewer/attachment}
                        .{Attachment/id}
                    .{+}
                        /datas
                [1]
                    [download]
                        true
`;
