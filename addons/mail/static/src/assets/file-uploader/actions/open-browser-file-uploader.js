/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            FileUploader/openBrowserFileUploader
        [Action/params]
            record
                [type]
                    FileUploader
        [Action/behavior]
            {UI/click}
                @record
                .{FileUploader/fileInput}
`;
