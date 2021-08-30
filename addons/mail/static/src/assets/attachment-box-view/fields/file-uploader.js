/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            fileUploader
        [Field/model]
            AttachmentBoxView
        [Field/type]
            one
        [Field/target]
            FileUploader
        [Field/isCausal]
            true
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
        [Field/inverse]
            FileUploader/attachmentBoxView
        [Field/default]
            {Record/insert}
                [Record/models]
                    FileUploader
`;
