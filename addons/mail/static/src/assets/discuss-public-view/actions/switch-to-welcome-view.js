/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Creates and displays the welcome view and clears the thread viewer.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DiscussPublicView/switchToWelcomeView
        [Action/params]
            record
                [type]
                    DiscussPublicView
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [DiscussPublicView/threadViewer]
                        {Record/insert}
                            [Record/models]
                                ThreadViewer
                    [DiscussPublicView/welcomeView]
                        {Record/insert}
                            [Record/models]
                                WelcomeView
                            [WelcomeView/channel]
                                @record
                                .{DiscussPublicView/channel}
                            [WelcomeView/isDoFocusGuestNameInput]
                                true
                            [WelcomeView/originalGuestName]
                                {Env/currentGuest}
                                .{&}
                                    {Env/currentGuest}
                                    .{Guest/name}
                            [WelcomeView/pendingGuestName]
                                {Env/currentGuest}
                                .{&}
                                    {Env/currentGuest}
                                    .{Guest/name}
            {if}
                @record
                .{DiscussPublicView/welcomeView}
                .{WelcomeView/mediaPreview}
            .{then}
                {MediaPreview/enableMicrophone}
                    @record
                    .{DiscussPublicView/welcomeView}
                    .{WelcomeView/mediaPreview}
                {MediaPreview/enableVideo}
                    @record
                    .{DiscussPublicView/welcomeView}
                    .{WelcomeView/mediaPreview}
`;
