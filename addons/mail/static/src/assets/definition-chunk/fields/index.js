/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            index
        [Field/model]
            DefinitionChunk
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/isRequired]
            true
`;
