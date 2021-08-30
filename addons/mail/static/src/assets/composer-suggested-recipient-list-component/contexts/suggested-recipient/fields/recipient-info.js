/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            recipientInfo
        [Field/model]
            ComposerSuggestedRecipientListComponent:suggestedRecipient
        [Field/type]
            one
        [Field/target]
            SuggestedRecipientInfo
        [Field/isRequired]
            true
`;
