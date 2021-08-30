/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            chatter
        [Field/model]
            AttachmentBoxView
        [Field/type]
            one
        [Field/target]
            Chatter
        [Field/isRequired]
            true
        [Field/inverse]
            Chatter/attachmentBoxView
        [Field/isReadonly]
            true
`;
