/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonAdd
        [Element/model]
            AttachmentBoxComponent
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-link
        [web.Element/type]
            button
        [Element/onClick]
            {web.Event/preventDefault}
                @ev
            {web.Event/stopPropagation}
                @ev
            {FileUploaderComponent/openBrowserFileUploader}
                @record
                .{AttachmentBoxComponent/fileUploader}
`;
