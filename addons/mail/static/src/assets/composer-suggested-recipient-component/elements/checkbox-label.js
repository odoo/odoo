/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            checkboxLabel
        [Element/model]
            ComposerSuggestedRecipientComponent
        [web.Element/tag]
            label
        [web.Element/class]
            custom-control-label
        [web.Element/for]
            @record
            .{ComposerSuggestedRecipientComponent/id}
            .{+}
                -checkbox
        [web.Element/textContent]
            {if}
                @record
                .{ComposerSuggestedRecipientComponent/suggestedRecipientInfo}
                .{SuggestedRecipientInfo/name}
                .{&}
                    @record
                    .{ComposerSuggestedRecipientComponent/suggestedRecipientInfo}
                    .{SuggestedRecipientInfo/email}
            .{then}
                {String/sprintf}
                    [0]
                        {Locale/text}
                            %s (%s)
                    [1]
                        @record
                        .{ComposerSuggestedRecipientComponent/suggestedRecipientInfo}
                        .{SuggestedRecipientInfo/name}
                    [2]
                        @record
                        .{ComposerSuggestedRecipientComponent/suggestedRecipientInfo}
                        .{SuggestedRecipientInfo/email}
            .{elif}
                @record
                .{ComposerSuggestedRecipientComponent/suggestedRecipientInfo}
                .{SuggestedRecipientInfo/name}
            .{then}
                @record
                .{ComposerSuggestedRecipientComponent/suggestedRecipientInfo}
                .{SuggestedRecipientInfo/name}
            .{else}
                @record
                .{ComposerSuggestedRecipientComponent/suggestedRecipientInfo}
                .{SuggestedRecipientInfo/email}
`;
