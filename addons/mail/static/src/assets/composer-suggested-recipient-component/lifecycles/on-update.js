/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Lifecycle
        [Lifecycle/name]
            onUpdate
        [Lifecycle/model]
            ComposerSuggestedRecipientComponent
        [Lifecycle/behavior]
            {if}
                @record
                .{ComposerSuggestedRecipientComponent/checkboxInput}
                .{&}
                    @record
                    .{ComposerSuggestedRecipientComponent/suggestedRecipientInfo}
            .{then}
                {Record/update}
                    [0]
                        @record
                        .{ComposerSuggestedRecipientComponent/checkboxInput}
                    [1]
                        [web.Element/isChecked]
                            @record
                            .{ComposerSuggestedRecipientComponent/suggestedRecipientInfo}
                            .{SuggestedRecipientInfo/isSelected}
`;
