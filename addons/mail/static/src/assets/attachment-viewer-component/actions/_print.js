/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Prompt the browser print of this attachment.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentViewerComponent/_print
        [Action/params]
            record
        [Action/behavior]
            :printWindow
                {Browser/open}
                    about:blank
                    _new
            {Document/open}
                @printWindow
                .{BrowserPrint/document}
            {Document/write}
                [0]
                    @printWindow
                    .{BrowserPrint/document}
                [1]
                    {html}
                        [html]
                            [head]
                                [script]
                                    :printImage
                                        {Record/insert}
                                            [Record/models]
                                                Function
                                            [Function/out]
                                                {Browser/print}
                                                {Browser/close}
                                    :onloadImage
                                        {Record/insert}
                                            [Record/models]
                                                Function
                                            [Function/out]
                                                {Browser/setTimeout}
                                                    []
                                                        @printImage
                                                        .{Function/call}
                                                    []
                                                        10
                            [body]
                                [body/onload]
                                    @onloadImage
                                    .{Function/call}
                                [img]
                                    [img/src]
                                        @record
                                        .{AttachmentViewerComponent/record}
                                        .{AttachmentViewer/attachment}
                                        .{Attachment/defaultSource}
            {Document/close}
                @printWindow
                .{BrowserPrint/document}
`;
