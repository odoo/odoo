/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            part1Partner
        [Element/model]
            ComposerSuggestionComponent
        [web.Element/tag]
            span
        [Record/models]
            ComposerSuggestionComponent/part1
        [Element/isPresent]
            @record
            .{ComposerSuggestionComponent/modelName}
            .{=}
                Partner
        [web.Element/textContent]
            @record
            .{ComposerSuggestionComponent/record}
            .{Partner/nameOrDisplayName}
`;
