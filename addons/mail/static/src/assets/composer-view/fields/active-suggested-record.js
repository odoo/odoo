/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the suggested record that is currently active. This record
        is highlighted in the UI and it will be the selected record if the
        suggestion is confirmed by the user.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            activeSuggestedRecord
        [Field/model]
            ComposerView
        [Field/type]
            one
        [Field/target]
            Record
        [Field/compute]
            {Dev/comment}
                Clears the active suggested record on closing mentions or adapt it if
                the active current record is no longer part of the suggestions.
            {if}
                @record
                .{ComposerView/mainSuggestedRecords}
                .{Collection/length}
                .{=}
                    0
                .{&}
                    @record
                    .{ComposerView/extraSuggestedRecords}
                    .{Collection/length}
                    .{=}
                        0
            .{then}
                {Record/empty}
            .{elif}
                @record
                .{ComposerView/mainSuggestedRecords}
                .{Collection/includes}
                    @record
                    .{ComposerView/activeSuggestedRecord}
                .{|}
                    @record
                    .{ComposerView/extraSuggestedRecords}
                    .{Collection/includes}
                        @record
                        .{ComposerView/activeSuggestedRecord}
            .{then}
                {break}
            .{else}
                :suggestedRecords
                    @record
                    .{ComposerView/mainSuggestedRecords}
                    .{Collection/concat}
                        @record
                        .{ComposerView/extraSuggestedRecords}
                :firstRecord
                    @suggestedRecords
                    .{Collection/first}
                @firstRecord
`;
