/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            ComposerSuggestedRecipientComponent
        [web.Element/data-partner-id]
            {if}
                @record
                .{ComposerSuggestedRecipientComponent/suggestedRecipientInfo}
                .{SuggestedRecipientInfo/partner}
                .{isFalsy}
            .{then}
                {break}
            {if}
                @record
                .{ComposerSuggestedRecipientComponent/suggestedRecipientInfo}
                .{SuggestedRecipientInfo/partner}
                .{Partner/id}
                .{isFalsy}
            .{then}
                {break}
            @record
            .{ComposerSuggestedRecipientComponent/suggestedRecipientInfo}
            .{SuggestedRecipientInfo/partner}
            .{Partner/id}
        [web.Element/title]
            {if}
                @record
                .{ComposerSuggestedRecipientComponent/suggestedRecipientInfo}
                .{isFalsy}
            .{then}
                {break}
            {String/sprintf}
                [0]
                    {Locale/text}
                        Add as recipient and follower (reason: %s)
                [1]
                    @record
                    .{ComposerSuggestedRecipientComponent/suggestedRecipientInfo}
                    .{SuggestedRecipientInfo/reason}
        [web.Element/style]
            {web.scss/selector}
                [0]
                    .modal-body
                [1]
                    [web.scss/padding]
                        {scss/map-get}
                            {scss/$spacers}
                            0
`;
