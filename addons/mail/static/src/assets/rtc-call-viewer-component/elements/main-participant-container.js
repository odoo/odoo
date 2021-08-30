/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            mainParticipantContainer
        [Element/model]
            RtcCallViewerComponent
        [Element/isPresent]
            @record
            .{RtcCallViewerComponent/rtcCallViewer}
            .{RtcCallViewer/layout}
            .{!=}
                tiled
        [web.Element/class]
            justify-content-center
            mw-100
            mh-100
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex-grow]
                1
`;
