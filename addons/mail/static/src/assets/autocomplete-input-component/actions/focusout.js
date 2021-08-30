/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AutocompleteInputComponent/focusout
        [Action/params]
            record
        [Action/behavior]
            {UI/unfocus}
                @record
                .{AutocompleteInputComponent/root}
`;
