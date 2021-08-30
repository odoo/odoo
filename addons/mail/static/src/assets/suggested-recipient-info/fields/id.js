/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the id of this suggested recipient info. This id does not
        correspond to any specific value, it is just a unique identifier
        given by the creator of this record.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            id
        [Field/model]
            SuggestedRecipientInfo
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/isReadonly]
            true
`;
