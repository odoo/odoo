/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            changeLayoutContent
        [Element/model]
            RtcCallViewerComponent
        [Field/target]
            RtcLayoutMenuComponent
        [RtcLayoutMenuComponent/rtcLayoutMenu]
            @record
            .{RtcCallViewerComponent/rtcCallViewer}
            .{RtcCallViewer/rtcLayoutMenu}
`;
