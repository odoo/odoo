/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines if the controller is an overlay or a bottom bar.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isControllerFloating
        [Field/model]
            RtcCallViewer
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
        [Field/compute]
            @record
            .{RtcCallViewer/isFullScreen}
            .{|}
                @record
                .{RtcCallViewer/layout}
                .{!=}
                    tiled
                .{&}
                    @record
                    .{RtcCallViewer/threadView}
                    .{ThreadView/compact}
                    .{isFalsy}
`;
