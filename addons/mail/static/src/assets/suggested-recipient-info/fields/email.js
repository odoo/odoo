/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the email of 'this'. It serves as visual clue when
        displaying 'this', and also serves as default partner email when
        creating a new partner from 'this'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            email
        [Field/model]
            SuggestedRecipientInfo
        [Field/type]
            attr
        [Field/target]
            String
        [Field/isReadonly]
            true
`;
