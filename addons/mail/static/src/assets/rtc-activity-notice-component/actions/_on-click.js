/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcActivityNoticeComponent/_onClick
        [Action/params]
            ev
                [type]
                    MouseEvent
            record
                [type]
                    RtcActivityNoticeComponent
        [Action/behavior]
            {Thread/open}
                {Rtc/channel}
`;
