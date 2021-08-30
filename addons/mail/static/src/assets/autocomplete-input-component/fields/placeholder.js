/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            placeholder
        [Field/model]
            AutocompleteInputComponent
        [Field/type]
            attr
        [Field/target]
            String
`;
