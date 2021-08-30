/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            suggestedRecipientForeach
        [Element/model]
            ComposerSuggestedRecipientListComponent
        [Record/models]
            Foreach
        [Field/target]
            ComposerSuggestedRecipientListComponent:suggestedRecipient
        [Element/isPresent]
            @record
            .{ComposerSuggestedRecipientListComponent/thread}
        [ComposerSuggestedRecipientListComponent:suggestedRecipient/recipientInfo]
            @field
            .{Foreach/get}
                recipientInfo
        [Foreach/collection]
            {if}
                @record
                .{ComposerSuggestedRecipientListComponent/hasShowMoreButton}
            .{then}
                @record
                .{ComposerSuggestedRecipientListComponent/thread}
                .{Thread/suggestedRecipientInfoList}
            .{else}
                @record
                .{ComposerSuggestedRecipientListComponent/thread}
                .{Thread/suggestedRecipientInfoList}
                .{Collection/slice}
                    0
                    3
        [Foreach/as]
            recipientInfo
        [Element/key]
            @field
            .{Foreach/get}
                recipientInfo
            .{Record/id}
`;
