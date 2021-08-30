/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines if the tiles are in a minimized format:
        small circles instead of cards, smaller display area.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isMinimized
        [Field/model]
            RtcCallViewer
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
        [Field/compute]
            {if}
                @record
                .{RtcCallViewer/threadView}
                .{isFalsy}
            .{then}
                true
            .{elif}
                @record
                .{RtcCallViewer/isFullScreen}
                .{|}
                    @record
                    .{RtcCallViewer/threadView}
                    .{ThreadView/compact}
            .{then}
                false
            .{else}
                @record
                .{RtcCallViewer/threadView}
                .{ThreadView/thread}
                .{Thread/rtc}
                .{isFalsy}
                .{|}
                    @record
                    .{RtcCallViewer/threadView}
                    .{ThreadView/thread}
                    .{Thread/videoCount}
                    .{=}
                        0
`;
