/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            options
        [Element/model]
            RtcOptionListComponent
        [Record/models]
            RtcOptionListComponent/button
        [Element/onClick]
            {RtcOptionList/onClickOptions}
                [0]
                    @record
                    .{RtcOptionListComponent/rtcOptionList}
                [1]
                    @ev
`;
