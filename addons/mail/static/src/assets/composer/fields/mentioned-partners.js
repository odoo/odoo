/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Detects if mentioned partners are still in the composer text input content
        and removes them if not.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            mentionedPartners
        [Field/model]
            Composer
        [Field/type]
            many
        [Field/target]
            Partner
        [Field/compute]
            :unmentionedPartners
                {Record/insert}
                    [Record/models]
                        Collection
            {Dev/comment}
                ensure the same mention is not used multiple times if multiple
                partners have the same name
            :namesIndex
                {Record/insert}
                    [Record/models]
                        Dict
            {foreach}
                @record
                .{Composer/mentionedPartners}
            .{as}
                partner
            .{do}
                :index
                    @record
                    .{Composer/textInputContent}
                    .{String/indexOf}
                        [0]
                            @
                            .{+}
                                @partner
                                .{Partner/name}
                        [1]
                            {if}
                                @namesIndex
                                .{Dict/at}
                                    @partner
                                    .{Partner/name}
                                .{!=}
                                    undefined
                            .{then}
                                @namesIndex
                                .{Dict/at}
                                    @partner
                                    .{Partner/name}
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
                                    @partner
                                    .{Partner/name}
                                [value]
                                    @index
                .{else}
                    @unmentionedPartners
                    .{Collection/push}
                        @partner
            {Field/remove}
                @unmentionedPartners
`;
