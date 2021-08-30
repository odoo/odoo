/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Sets the first suggestion as active. Main and extra records are
        considered together.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ComposerView/setFirstSuggestionActive
        [Action/params]
            record
                [type]
                    ComposerView
        [Action/behavior]
            :suggestedRecords
                @record
                .{ComposerView/mainSuggestedRecords}
                .{Collection/concat}
                    @record
                    .{ComposerView/extraSuggestedRecords}
            :firstRecord
                @suggestedRecords
                .{Collection/first}
            {Record/update}
                [0]
                    @record
                [1]
                    [ComposerView/activeSuggestedRecord]
                        @firstRecord
`;
