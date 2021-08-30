/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            suggestedRecipient
        [Element/model]
            ComposerSuggestedRecipientListComponent:suggestedRecipient
        [Field/target]
            ComposerSuggestedRecipientComponent
        [ComposerSuggestedRecipientComponent/suggestedRecipientInfo]
            @record
            .{ComposerSuggestedRecipientListComponent:suggestedRecipient/recipientInfo}
`;
