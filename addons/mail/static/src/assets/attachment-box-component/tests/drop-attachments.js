/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            drop attachments
        [Test/model]
            AttachmentBoxComponent
        [Test/assertions]]
            5
        [Test/scenario]
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
            @testEnv
            .{Record/insert}
                [Record/models]
                    ChatterContainerComponent
                [ChatterContainerComponent/isAttachmentBoxVisibleInitially]
                    true
                [ChatterContainerComponent/threadId]
                    100
                [ChatterContainerComponent/threadModel]
                    res.partner
            :files
                {Record/insert}
                    [Record/models]
                        web.File
                    [web.File/content]
                        hello, world
                    [web.File/contentType]
                        text/plain
                    [web.File/name]
                        text.txt
            {Test/assert}
                []
                    @thread
                    .{Thread/attachmentBoxComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have an attachment box

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/dragenterFiles}
                    [0]
                        @thread
                        .{Thread/attachmentBoxComponents}
                        .{Collection/first}
                    [1]
                        @files
            {Test/assert}
                []
                    @thread
                    .{Thread/attachmentBoxComponents}
                    .{Collection/first}
                    .{AttachmentBoxComponent/dropZone}
                []
                    should have a drop zone
            {Test/assert}
                []
                    @thread
                    .{Thread/attachments}
                    .{Collection/first}
                    .{Attachment/attachmentComponents}
                    .{Collection/length}
                    .{=}
                        0
                []
                    should have no attachment before files are dropped

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/dropFiles}
                    [0]
                        @thread
                        .{Thread/attachmentBoxComponents}
                        .{Collection/first}
                        .{AttachmentBoxComponent/dropZone}
                    [1]
                        @files
            {Test/assert}
                []
                    @thread
                    .{Thread/attachments}
                    .{Collection/first}
                    .{Attachment/attachmentComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have 1 attachment in the box after files dropped

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/dragenterFiles}
                    @thread
                    .{Thread/attachmentBoxComponents}
                    .{Collection/first}
            :file1
                {Record/insert}
                    [Record/models]
                        web.File
                    [web.File/content]
                        hello, world
                    [web.File/contentType]
                        text/plain
                    [web.File/name]
                        text2.txt
            :file2
                {Record/insert}
                    [Record/models]
                        web.File
                    [web.File/content]
                        hello, world
                    [web.File/contentType]
                        text/plain
                    [web.File/name]
                        text3.txt
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/dropFiles}
                    [0]
                        @thread
                        .{Thread/attachmentBoxComponents}
                        .{Collection/first}
                        .{AttachmentBoxComponent/dropZone}
                    [1]
                        @file1
                        @file2
            {Test/assert}
                []
                    @thread
                    .{Thread/attachments}
                    .{Collection/length}
                    .{=}
                        3
                []
                    should have 3 attachments in the box after files dropped
`;
