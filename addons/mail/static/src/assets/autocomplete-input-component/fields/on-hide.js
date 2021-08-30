/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            onHide
        [Field/model]
            AutocompleteInputComponent
        [Field/type]
            attr
        [Field/target]
            Function
        [Field/isOptional]
            true
`;
