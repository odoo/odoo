/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            part1Command
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
                ChannelCommand
        [web.Element/textContent]
            @record
            .{ComposerSuggestionComponent/record}
            .{ChannelCommand/name}
`;
