/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the extra records that are currently suggested.
        Allows to have different model types of mentions through a dynamic
        process. 2 arbitrary lists can be provided and the second is defined
        as "extra".
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            extraSuggestedRecords
        [Field/model]
            ComposerView
        [Field/type]
            many
        [Field/target]
            Record
        [Field/compute]
            {Dev/comment}
                Clears the extra suggested record on closing mentions, and ensures
                the extra list does not contain any element already present in the
                main list, which is a requirement for the navigation process.
            {if}
                @record
                .{ComposerView/suggestionDelimiterPosition}
                .{=}
                    undefined
            .{then}
                {Record/empty}
            .{else}
                {Field/remove}
                    @record
                    .{ComposerView/mainSuggestedRecords}
`;
