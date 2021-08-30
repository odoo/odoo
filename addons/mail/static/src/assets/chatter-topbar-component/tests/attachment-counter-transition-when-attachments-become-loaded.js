/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            attachment counter transition when attachments become loaded
        [Test/model]
            ChatterTopbarComponent
        [Test/assertions]
            7
        [Test/scenario]
            :attachmentPromise
                {Record/insert}
                    [Record/models]
                        Deferred
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [Record/models]
                    res.partner
                [res.partner/id]
                    100
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
                [Server/mockRPC]
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            route
                            args
                            original
                        [Function/out]
                            {if}
                                @route
                                .{String/includes}
                                    /mail/thread/data
                            .{then}
                                {Promise/await}
                                    @attachmentPromise
                            @original
            @testEnv
            .{Record/insert}
                [Record/models]
                    ChatterContainerComponent
                [ChatterContainerComponent/threadId]
                    100
                [ChatterContainerComponent/threadModel]
                    res.partner
            {Test/assert}
                []
                    @chatter
                    .{Chatter/chatterTopbarComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have a chatter topbar
            {Test/assert}
                []
                    @chatter
                    .{Chatter/chatterTopbarComponents}
                    .{Collection/first}
                    .{ChatterTopbarComponent/buttonAttachments}
                []
                    should have an attachments button in chatter menu
            {Test/assert}
                []
                    @chatter
                    .{Chatter/chatterTopbarComponents}
                    .{Collection/first}
                    .{ChatterTopbarComponent/buttonAttachmentsCountLoader}
                []
                    attachments button should have a loader
            {Test/assert}
                []
                    @chatter
                    .{Chatter/chatterTopbarComponents}
                    .{Collection/first}
                    .{ChatterTopbarComponent/buttonAttachmentsCount}
                    .{isFalsy}
                []
                    attachments button should not have a counter

            @testEnv
            .{Component/afterNextRender}
                {Promise/resolve}
                    @attachmentPromise
            {Test/assert}
                []
                    @chatter
                    .{Chatter/chatterTopbarComponents}
                    .{Collection/first}
                    .{ChatterTopbarComponent/buttonAttachments}
                []
                    should have an attachments button in chatter menu
            {Test/assert}
                []
                    @chatter
                    .{Chatter/chatterTopbarComponents}
                    .{Collection/first}
                    .{ChatterTopbarComponent/buttonAttachmentsCountLoader}
                    .{isFalsy}
                []
                    attachments button should not have a loader
            {Test/assert}
                []
                    @chatter
                    .{Chatter/chatterTopbarComponents}
                    .{Collection/first}
                    .{ChatterTopbarComponent/buttonAttachmentsCount}
                []
                    attachments button should have a counter
`;
