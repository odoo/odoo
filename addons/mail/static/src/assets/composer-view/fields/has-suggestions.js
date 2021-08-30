/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether there is any result currently found for the current
        suggestion delimiter and search term, if applicable.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasSuggestions
        [Field/model]
            ComposerView
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
        [Field/compute]
            @record
            .{ComposerView/mainSuggestedRecords}
            .{Collection/length}
            .{>}
                0
            .{|}
                @record
                .{ComposerView/extraSuggestedRecords}
                .{Collection/length}
                .{>}
                    0
`;
