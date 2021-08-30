/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            downloadLogs
        [Element/model]
            RtcOptionListComponent
        [Record/models]
            RtcOptionListComponent/button
        [Element/isPresent]
            {Env/isDebug}
        [Element/onClick]
            {RtcOptionList/onClickDownloadLogs}
                [0]
                    @record
                    .{RtcOptionListComponent/rtcOptionList}
                [1]
                    @ev
`;
