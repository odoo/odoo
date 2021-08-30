/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the 'SuggestedRecipientInfo' concerning 'this'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            suggestedRecipientInfoList
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            SuggestedRecipientInfo
        [Field/inverse]
            SuggestedRecipientInfo/thread
        [Field/isCausal]
            true
`;
