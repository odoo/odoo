/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            DefinitionChunk
        [Model/fields]
            definition
            elementOf
            elements
            index
            level
            semanticallyNext
            semanticallyPrevious
            structuralNext
            structuralPrevious
            relevantPart
            type
        [Model/id]
            DefinitionChunk/definition
            .{&}
                DefinitionChunk/index
`;
