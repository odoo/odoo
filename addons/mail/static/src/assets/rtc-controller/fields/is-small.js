/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isSmall
        [Field/model]
            RtcController
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{RtcController/callViewer}
            .{&}
                @record
                .{RtcController/callViewer}
                .{RtcCallViewer/threadView}
                .{ThreadView/compact}
            .{&}
                @record
                .{RtcController/callViewer}
                .{RtcCallViewer/isFullScreen}
                .{isFalsy}
`;
