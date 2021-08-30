/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            elementOf
        [Field/model]
            DefinitionChunk
        [Field/type]
            one
        [Field/target]
            DefinitionChunk
        [Field/inverse]
            DefinitionChunk/elements
`;
