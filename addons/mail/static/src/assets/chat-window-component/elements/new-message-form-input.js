/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            newMessageFormInput
        [Element/model]
            ChatWindowComponent
        [Field/target]
            AutocompleteInputComponent
        [AutocompleteInputComponent/placeholder]
            {Locale/text}
                Search user...
        [AutocompleteInputComponent/select]
            {ChatWindowComponent/_onAutocompleteSelect}
                @record
                @args
        [AutocompleteInputComponent/source]
            {ChatWindowComponent/_onAutocompleteSource}
                @record
                @args
        [Element/onFocusin]
            {ChatWindow/onFocusInNewMessageFormInput}
                [0]
                    @record
                    .{ChatWindowComponent/chatWindow}
                [1]
                    @ev
        [web.Element/style]
            [web.scss/flex]
                1
                1
                auto
            [web.scss/outline]
                none
            [web.scss/border]
                {scss/$border-width}
                solid
                {web.scss/gray}
                    300
                {Dev/comment}
                    cancel firefox border on input focus
`;
