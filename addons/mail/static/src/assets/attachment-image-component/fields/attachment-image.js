/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachmentImage
        [Field/model]
            AttachmentImageComponent
        [Field/type]
            one
        [Field/target]
            AttachmentImage
        [Field/inverse]
            AttachmentImage/component
`;
