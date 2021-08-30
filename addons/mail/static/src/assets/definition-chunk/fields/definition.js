/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            definition
        [Field/model]
            DefinitionChunk
        [Field/type]
            one
        [Field/target]
            Definition
        [Field/isRequired]
            true
        [Field/inverse]
            Definition/lines
`;
