/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            exitFullscreen
        [Element/model]
            RtcOptionListComponent
        [Record/models]
            RtcOptionListComponent/button
        [Element/isPresent]
            @record
            .{RtcOptionListComponent/rtcOptionList}
            .{RtcOptionList/rtcController}
            .{RtcController/callViewer}
            .{RtcCallViewer/isFullScreen}
        [Element/onClick]
            {RtcOptionList/onClickDeactivateFullscreen}
                [0]
                    @record
                    .{RtcOptionListComponent/rtcOptionList}
                [1]
                    @ev
`;
