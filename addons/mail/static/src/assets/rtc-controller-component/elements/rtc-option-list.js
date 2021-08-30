/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            rtcOptionList
        [Element/model]
            RtcControllerComponent
        [Field/target]
            RtcOptionListComponent
        [RtcOptionListComponent/rtcOptionList]
            @record
            .{RtcControllerComponent/rtcController}
            .{RtcController/rtcOptionList}
`;
