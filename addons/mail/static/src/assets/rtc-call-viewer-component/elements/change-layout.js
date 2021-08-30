/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            changeLayout
        [Element/model]
            RtcCallViewerComponent
        [Field/target]
            DialogComponent
        [Element/isPresent]
            @record
            .{RtcCallViewerComponent/rtcCallViewer}
            .{RtcCallViewer/rtcLayoutMenu}
        [DialogComponent/size]
            small
        [DialogComponent/title]
            @record
            .{RtcCallViewerComponent/rtcCallViewer}
            .{RtcCallViewer/layoutSettingsTitle}
        [DialogComponent/onClosed]
            {RtcCallViewer/onRtcSettingsDialogClosed}
                [0]
                    @record
                    .{RtcCallViewerComponent/rtcCallViewer}
                [1]
                    @ev
`;
