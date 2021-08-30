/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            onChange
        [onChange/name]
            RtcCallViewer/_onChangeVideoCount
        [onChange/model]
            RtcCallViewer
        [onChange/dependencies]
            RtcCallViewer/threadView
                ThreadView/thread
                    Thread/videoCount
        [onChange/behavior]
            {if}
                @record
                .{RtcCallViewer/threadView}
                .{ThreadView/thread}
                .{Thread/videoCount}
                .{=}
                    0
            .{then}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [RtcCallViewer/filterVideoGrid]
                            false
`;
