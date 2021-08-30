/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            chunks
        [Field/model]
            Definition
        [Field/type]
            many
        [Field/target]
            DefinitionChunk
        [Field/inverse]
            DefinitionChunk/definition
`;
