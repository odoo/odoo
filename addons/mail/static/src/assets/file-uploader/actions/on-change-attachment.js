/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Called when there are changes in the file input.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            FileUploader/onChangeAttachment
        [Action/params]
            ev
                [type]
                    web.Event
                [description]
                    ev.target.files
                        [type]
                            web.FileList
                            .{|}
                                Array
            record
                [type]
                    FileUploader
        [Action/behavior]
            {FileUploader/uploadFiles}
                [0]
                    @record
                [1]
                    @ev
                    .{web.Event/target}
                    .{web.Element/files}
`;
