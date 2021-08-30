/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the media preview embedded in this welcome view.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            mediaPreview
        [Field/model]
            WelcomeView
        [Field/type]
            one
        [Field/target]
            MediaPreview
        [Field/isCausal]
            true
        [Field/isReadonly]
            true
        [Field/inverse]
            MediaPreview/welcomeView
        [Field/compute]
            {if}
                @record
                .{WelcomeView/channel}
                .{&}
                    @record
                    .{WelcomeView/channel}
                    .{Thread/defaultDisplayMode}
                    .{=}
                        video_full_screen
            .{then}
                {Record/insert}
                    [Record/models]
                        MediaPreview
            .{else}
                {Record/empty}
`;
