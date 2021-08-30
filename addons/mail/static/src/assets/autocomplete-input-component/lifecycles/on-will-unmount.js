/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Lifecycle
        [Lifecycle/name]
            onWillUnmount
        [Lifecycle/model]
            AutocompleteInputComponent
        [Lifecycle/behavior]
            {Record/insert}
                [Record/models]
                    jQuery
                @record
                .{AutocompleteInputComponent/root}
            .{jQuery/autocomplete}
                destroy
`;
