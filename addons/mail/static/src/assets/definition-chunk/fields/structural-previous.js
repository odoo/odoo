/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            structuralPrevious
        [Field/model]
            DefinitionChunk
        [Field/type]
            one
        [Field/target]
            DefinitionChunk
        [Field/inverse]
            DefinitionChunk/structuralNext
`;
