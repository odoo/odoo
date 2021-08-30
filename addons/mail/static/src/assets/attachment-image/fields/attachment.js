/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the attachment of this attachment image.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachment
        [Field/model]
            AttachmentImage
        [Field/type]
            one
        [Field/target]
            Attachment
        [Field/isRequired]
            true
        [Field/isReadonly]
            true
`;
