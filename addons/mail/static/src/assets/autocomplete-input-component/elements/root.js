/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            AutocompleteInputComponent
        [web.Element/tag]
            input
        [Element/onBlur]
            {AutocompleteInputComponent/_hide}
                @record
        [Element/onKeydown]
            {if}
                @ev
                .{web.KeyboardEvent/key}
                .{=}
                    Escape
            .{then}
                {AutocompleteInputComponent/_hide}
                    @record
        [web.Element/placeholder]
            @record
            .{AutocompleteInputComponent/placeholder}
`;
