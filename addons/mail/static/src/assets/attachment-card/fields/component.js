/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the OWL component of this attachment card.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            component
        [Field/model]
            AttachmentCard
        [Field/type]
            attr
        [Field/target]
            AttachmentCardComponent
`;
