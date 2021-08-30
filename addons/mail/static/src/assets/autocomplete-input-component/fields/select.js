/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            select
        [Field/model]
            AutocompleteInputComponent
        [Field/type]
            attr
        [Field/target]
            Function
`;
