/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the target model name of the suggestion currently in progress,
        if any.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            suggestionModelName
        [Field/model]
            ComposerView
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {switch}
                @record
                .{ComposerView/suggestionDelimiter
            .{then}
                [@]
                    Partner
                [:]
                    CannedResponse
                [/]
                    ChannelCommand
                [#]
                    Thread
                []
                    {Record/empty}
`;
