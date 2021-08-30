/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Sets the last suggestion as active. Main and extra records are
        considered together.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ComposerView/setLastSuggestionActive
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
            :lastRecord
                @suggestedRecords
                .{Collection/last}
            {Record/update}
                [0]
                    @record
                [1]
                    [ComposerView/activeSuggestedRecord]
                        @lastRecord
`;
