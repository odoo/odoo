/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentViewerComponent/_hideUnwantedPdfJsButtons
        [Action/params]
            record
        [Action/behavior]
            {if}
                @record
                .{AttachmentViewerComponent/viewPdf}
            .{then}
                {Dev/comment}
                    hidePDFJSButtons
                @record
                .{AttachmentViewerComponent/viewPdf}
`;
