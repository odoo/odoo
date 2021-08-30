/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            rtcController
        [Element/model]
            RtcCallViewerComponent
        [web.Element/target]
            RtcControllerComponent
        [RtcControllerComponent/rtcController]
            @record
            .{RtcCallViewerComponent/rtcCallViewer}
            .{RtcCallViewer/rtcController}
`;
