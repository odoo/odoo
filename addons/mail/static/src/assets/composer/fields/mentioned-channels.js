/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Detects if mentioned channels are still in the composer text input content
        and removes them if not.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            mentionedChannels
        [Field/model]
            Composer
        [Field/type]
            many
        [Field/target]
            Thread
        [Field/compute]
            :unmentionedChannels
                {Record/insert}
                    [Record/models]
                        Collection
            {Dev/comment}
                ensure the same mention is not used multiple times if multiple
                channels have the same name
            :namesIndex
                {Record/insert}
                    [Recod/models]
                        Dict
            {foreach}
                @record
                .{Composer/mentionedChannels}
            .{as}
                channel
            .{do}
                :index
                    @record
                    .{Composer/textInputContent}
                    .{String/indexOf}
                        [0]
                            #
                            .{+}
                                @channel
                                .{Thread/name}
                        [1]
                            {if}
                                @namesIndex
                                .{Dict/at}
                                    @channel
                                    .{Thread/name}
                                .{!=}
                                    undefined
                            .{then}
                                @namesIndex
                                .{Dict/at}
                                    @channel
                                    .{Thread/name}
                                .{+}
                                    1
                            .{else}
                                0
                {if}
                    @index
                    .{!=}
                        -1
                .{then}
                    {Record/update}
                        [0]
                            @namesIndex
                        [1]
                            {association}
                                [key]
                                    @channel
                                    .{Thread/name}
                                [value]
                                    @index
                .{else}
                    {Collection/push}
                        @unmentionedChannels
                        @channel
            {Field/remove}
                @unmentionedChannels
`;
