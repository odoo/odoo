/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        When images are displayed using 'src' attribute for the 1st time, it fetches the resource.
        In this case, images are actually displayed (fully fetched and rendered on screen) when
        '<image>' intercepts 'load' event.

        Current code needs to be aware of load state of image, to display spinner when loading
        and actual image when loaded. This test asserts no crash from mishandling image becoming
        loaded from being viewed for 1st time, but viewer being closed while image is loading.
    {Test}
        [Test/name]
            does not crash when the viewer is closed before image load
        [Test/model]
            AttachmentListComponent
        [Test/isTechnical]
            true
        [Test/assertions]
            1
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
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
                    DialogManagerComponent
            :attachment
                @testEnv
                .{Record/insert}
                    [Record/models]
                        Attachment
                    [Attachment/filename]
                        test.png
                    [Attachment/id]
                        750
                    [Attachment/mimetype]
                        image/png
                    [Attachment/name]
                        test.png
            :message
                @testEnv
                .{Record/insert}
                    [Record/models]
                        Message
                    [Message/attachments]
                        {Field/add}
                            @attachment
                    [Message/author]
                        @testEnv
                        .{Env/currentPartner}
                    [Message/body]
                        <p>Test</p>
                    [Message/id]
                        100
            @testEnv
            .{Record/insert}
                [Record/models]
                    MessageViewComponent
                [MessageViewComponent/messageView]
                    {Record/insert}
                        [Record/models]
                            MessageView
                        [MessageView/message]
                            @message
            @testEnv
            .{UI/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            AttachmentImageComponent
                    .{Collection/first}
            :imageEl
                @testEnv
                .{DialogManager/dialogs}
                .{Collection/first}
                .{Dialog/attachmentViewer}
                .{AttachmentViewer/attachmentViewerComponents}
                .{Collection/first}
                .{AttachmentViewerComponent/viewImage}

            @testEnv
            .{UI/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{DialogManager/dialogs}
                    .{Collection/first}
                    .{Dialog/attachmentViewer}
                    .{AttachmentViewer/attachmentViewerComponents}
                    .{Collection/first}
                    .{AttachmentViewerComponent/headerItemButtonClose}
            {Dev/comment}
                Simulate image becoming loaded.
            {try}
                @testEnv
                .{web.Element/dispatch}
                    [0]
                        @imageEl
                    [1]
                        {Record/insert}
                            [Record/models]
                                Event
                            [0]
                                load
                            [1]
                                [bubbles]
                                    true
                :successfulLoad
                    true
            .{catch}
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        err
                    [Function/out]
                        :successfulLoad
                            false
            .{finally}
                {Test/assert}
                    []
                        @successfulLoad
                    []
                        should not crash when the image is loaded
`;
