/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            AutocompleteInputComponent
        [Model/fields]
            customClass
            doFocus
            isFocusOnMount
            isHtml
            onHide
            placeholder
            select
            source
        [Model/template]
            root
        [Model/actions]
            AutocompleteInputComponent/_hide
            AutocompleteInputComponent/contains
            AutocompleteInputComponent/focus
            AutocompleteInputComponent/_onAutocompleteFocus
            AutocompleteInputComponent/_onAutocompleteSelect
            AutocompleteInputComponent/_onAutocompleteSource
        [Model/lifecycles]
            onMounted
            onWillUnmount
`;
