/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            startMeetingButton
        [Element/model]
            DiscussSidebarComponent
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-primary
            rounded
        [web.Element/title]
            {Locale/text}
                Start a meeting
        [Element/onClick]
            {Discuss/onClickStartAMeetingButton}
                [0]
                    @record
                [1]
                    @ev
`;
