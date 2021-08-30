/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcCallViewer/_onFullScreenChange
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
                {Record/update}
                    [0]
                        @record
                    [1]
                        [RtcCallViewer/isFullScreen]
                            true
            .{else}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [RtcCallViewer/isFullScreen]
                            false
`;
