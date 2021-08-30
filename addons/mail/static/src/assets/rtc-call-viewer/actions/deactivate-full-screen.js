/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcCallViewer/deactivateFullScreen
        [Action/params]
            record
                [type]
                    RtcCallViewer
        [Action/behavior]
            :fullScreenElement
                {web.Browser/document}
                .{web.Document/webkitFullscreenElement}
                .{|}
                    {web.Browser/document}
                    .{web.Document/fullscreenElement}
            {if}
                @fullScreenElement
            .{then}
                {if}
                    {web.Browser/document}
                    .{Document/exitFullscreen}
                .{then}
                    {web.Browser/document}
                    .{web.Document/exitFullscreen}
                    .{Function/call}
                .{elif}
                    {web.Browser/document}
                    .{web.Document/mozCancelFullScreen}
                .{then}
                    {web.Browser/document}
                    .{web.Document/mozCancelFullScreen}
                    .{Function/call}
                .{elif}
                    {web.Browser/document}
                    .{web.Document/webkitCancelFullScreen}
                .{then}
                    {web.Browser/document}
                    .{web.Document/webkitCancelFullScreen}
                    .{Function/call}
            {if}
                {Record/exists}
                    @record
            .{then}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [RtcCallViewer/isFullScreen]
                            false
`;
