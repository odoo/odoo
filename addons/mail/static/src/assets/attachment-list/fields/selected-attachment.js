/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            selectedAttachment
        [Field/model]
            AttachmentList
        [Field/type]
            one
        [Field/target]
            Attachment
`;
