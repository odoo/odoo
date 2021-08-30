/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the attachment of this card.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            attachment
        [Field/model]
            AttachmentCard
        [Field/type]
            one
        [Field/target]
            Attachment
        [Field/isRequired]
            true
`;
