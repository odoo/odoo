/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachmentCard
        [Field/model]
            AttachmentCardComponent
        [Field/type]
            one
        [Field/target]
            AttachmentCard
        [Field/inverse]
            AttachmentCard/component
`;
