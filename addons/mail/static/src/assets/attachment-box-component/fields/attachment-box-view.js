/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachmentBoxView
        [Field/model]
            AttachmentBoxComponent
        [Field/type]
            one
        [Field/target]
            AttachmentBoxView
        [Field/isRequired]
            true
        [Field/inverse]
            AttachmentBoxView/component
`;
