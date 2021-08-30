/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Making sure that dragging content is external files.
        Ignoring other content dragging like text.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DropZoneComponent/_isDragSourceExternalFile
        [Action/params]
            dataTransfer
            record
        [Action/behavior]
            @dataTransfer
            .{DataTransfer/types}
            .{Collection/includes}
                Files
`;
