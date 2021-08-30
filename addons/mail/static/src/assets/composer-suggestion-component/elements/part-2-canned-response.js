/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            part2CannedResponse
        [Element/model]
            ComposerSuggestionComponent
        [web.Element/tag]
            span
        [Record/models]
            ComposerSuggestionComponent/part2
        [Element/isPresent]
            @record
            .{ComposerSuggestionComponent/modelName}
            .{=}
                CannedResponse
        [web.Element/textContent]
            @record
            .{ComposerSuggestionComponent/record}
            .{CannedResponse/substitution}
`;
