/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the attachmentList displaying this card.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachmentList
        [Field/model]
            AttachmentCard
        [Field/type]
            one
        [Field/target]
            AttachmentList
        [Field/isRequired]
            true
        [Field/isReadonly]
            true
        [Field/inverse]
            AttachmentList/attachmentCards
`;
