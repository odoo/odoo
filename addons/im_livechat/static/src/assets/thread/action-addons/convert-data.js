/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ActionAddon
        [ActionAddon/action]
            Thread/convertData
        [ActionAddon/feature]
            im_livechat
        [ActionAddon/params]
            data
        [ActionAddon/behavior]
            :data2
                @original
            {if}
                @data
                .{Dict/hasKey}
                    livechat_visitor
                .{&}
                    @data
                    .{Dict/get}
                        livechat_visitor
            .{then}
                {if}
                    @data2
                    .{Thread/members}
                    .{isFalsy}
                .{then}
                    {Record/update}
                        [0]
                            @data2
                        [1]
                            Thread/members]
                                {Record/insert}
                                    [Record/models]
                                        Collection
                {Dev/comment}
                    livechat_visitor without id is the anonymous visitor.
                {if}
                    @data
                    .{Dict/get}
                        livechat_visitor
                        .{Dict/get}
                            id
                        .{isFalsy}
                .{then}
                    {Dev/comment}
                        Create partner derived from public partner and
                        replace the public partner.

                        Indeed the anonymous visitor is registered as a
                        member of the channel as the public partner in the
                        database to avoid polluting the contact list with
                        many temporary partners.

                        But the issue with public partner is that it is the
                        same record for every livechat, whereas every
                        correspondent should actually have its own visitor
                        name, typing status, etc.

                        Due to JS being temporary by nature there is no such
                        notion of polluting the database, it is therefore
                        acceptable and easier to handle one temporary partner
                        per channel.
                    {Record/update}
                        [0]
                            @data2
                        [1]
                            [Thread/members]
                                []
                                    @data2
                                    .{Thread/members}
                                []
                                    {Field/remove}
                                        {Env/publicPartners}
                    :partner
                        {Record/insert}
                            [Record/models]
                                Partner
                            {Partner/convertData}
                                @data
                                .{Dict/get}
                                    livechat_visitor
                                [Partner/id]
                                    {Partner/getNextPublicId}
                    {Record/update}
                        [0]
                            @data2
                        [1]
                            [Thread/correspondent]
                                @partner
                            [Thread/members]
                                []
                                    @data2
                                    .{Thread/members}
                                []
                                    @partner
                .{else}
                    :partnerData
                        {Partner/convertData}
                            @data
                            .{Dict/get}
                                livechat_visitor
                    {Record/update}
                        [0]
                            @data2
                        [1]
                            [Thread/correspondent]
                                {Record/insert}
                                    [Record/models]
                                        Partner
                                    @partnerData
                            [Thread/members]
                                []
                                    @data2
                                    .{Thread/members}
                                []
                                    {Record/insert}
                                        [Record/models]
                                            Partner
                                        @partnerData
            @data2
`;
