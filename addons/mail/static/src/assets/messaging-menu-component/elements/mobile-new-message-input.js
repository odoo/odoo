/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            mobileNewMessageInput
        [Element/model]
            MessagingMenuComponent
        [Field/target]
            AutocompleteInputComponent
        [Element/isPresent]
            {Device/isMobile}
            .{&}
                {MessagingMenu/isMobileNewMessageToggled}
        [AutocompleteInputComponent/customClass]
            @record
            .{MessagingMenuComponent/id}
            .{+}
                -mobileNewMessageInputAutocomplete
        [AutocompleteInputComponent/isFocusOnMount]
            true
        [AutocompleteInputComponent/placeholder]
            {Locale/text}
                Search user...
        [AutocompleteInputComponent/select]
            {MessagingMenuComponent/_onMobileNewMessageInputSelect}
                @record
        [AutocompleteInputComponent/source]
            {MessagingMenuComponent/_onMobileNewMessageInputSource}
                @record
        [web.Element/style]
            [web.scss/grid-area]
                bottom
            [web.scss/padding]
                {scss/map-get}
                    {scss/$spacers}
                    2
            [web.scss/margin-top]
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
                5px
            [web.scss/outline]
                none
`;
