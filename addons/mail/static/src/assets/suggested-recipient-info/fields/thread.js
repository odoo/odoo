/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the 'Thread' concerned by 'this.'
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            thread
        [Field/model]
            SuggestedRecipientInfo
        [Field/type]
            one
        [Field/target]
            Thread
        [Field/inverse]
            Thread/suggestedRecipientInfoList
        [Field/isRequired]
            true
`;
