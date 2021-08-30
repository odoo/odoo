/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines why 'this' is a suggestion for 'this.thread'. It serves as
        visual clue when displaying 'this'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            reason
        [Field/model]
            SuggestedRecipientInfo
        [Field/type]
            attr
        [Field/target]
            String
`;
