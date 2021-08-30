/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Context
        [Context/name]
            suggestedRecipient
        [Context/model]
            ComposerSuggestedRecipientListComponent
        [Model/fields]
            recipientInfo
        [Model/template]
            suggestedRecipientForeach
                suggestedRecipient
`;
