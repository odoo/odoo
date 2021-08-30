/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            elements
        [Field/model]
            DefinitionChunk
        [Field/type]
            many
        [Field/target]
            DefinitionChunk
        [Field/inverse]
            DefinitionChunk/elementOf
`;
