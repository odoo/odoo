/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            mobileAddItemHeaderInput
        [Element/model]
            DiscussComponent
        [Field/target]
            AutocompleteInputComponent
        [AutocompleteInputComponent/isFocusOnMount]
            true
        [AutocompleteInputComponent/isHtml]
            @record
            .{DiscussComponent/discussView}
            .{DiscussView/discuss}
            .{Discuss/isAddingChannel}
        [AutocompleteInputComponent/placeholder]
            {if}
                @record
                .{DiscussComponent/discussView}
                .{DiscussView/discuss}
                .{Discuss/isAddingChannel}
            .{then}
                {Locale/text}
                    Create or search channel...
            .{else}
                {Locale/text}
                    Search user...
        [AutocompleteInputComponent/select]
            {DiscussComponent/_onMobileAddItemHeaderInputSelect}
                @record
        [AutocompleteInputComponent/source]
            {DiscussComponent/_onMobileAddItemHeaderInputSource}
                @record
        [web.Element/style]
            [web.scss/flex]
                1
                1
                auto
            [web.scss/margin-bottom]
                {scss/map-get}
                    {scss/$spacers}
                    3
            [web.scss/padding]
                {scss/map-get}
                    {scss/$spacers}
                    2
            [web.scss/appearance]
                none
            [web.scss/border]
                {scss/$border-width}
                solid
                {scss/gray}
                    400
            [web.scss/border-radius]
                5
                px
            [web.scss/outline]
                none
`;
