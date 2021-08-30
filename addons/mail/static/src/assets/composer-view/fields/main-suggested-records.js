/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the main records that are currently suggested.
        Allows to have different model types of mentions through a dynamic
        process. 2 arbitrary lists can be provided and the first is defined
        as "main".
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            mainSuggestedRecords
        [Field/model]
            ComposerView
        [Field/type]
            many
        [Field/target]
            Record
        [Field/compute]
            {Dev/comment}
                Clears the main suggested record on closing mentions.
            {if}
                @record
                .{ComposerView/suggestionDelimiterPosition}
                .{=}
                    undefined
            .{then}
                {Record/empty}
`;
