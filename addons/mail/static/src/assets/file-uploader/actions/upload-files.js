/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            FileUploader/uploadFiles
        [Action/params]
            files
                [type]
                    web.FileList
                    .{|}
                        Array
            record
                [type]
                    FileUploader
        [Action/behavior]
            {FileUploader/_performUpload}
                [0]
                    @record
                [1]
                    [files]
                        @files
            {if}
                @record
                .{FileUploader/fileInput}
            .{then}
                {Record/update}
                    [0]
                        @record
                        .{FileUploader/fileInput}
                    [1]
                        [web.Element/value]
                            {Record/empty}
`;
