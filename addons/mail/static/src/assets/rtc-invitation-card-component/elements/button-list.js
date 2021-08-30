/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonList
        [Element/model]
            RtcInvitationCardComponent
        [web.Element/style]
            [web.scss/width]
                100%
            [web.scss/display]
                flex
            [web.scss/margin-top]
                {scss/map-get}
                    {scss/$spacers}
                    4
            [web.scss/justify-content]
                space-around
            [web.scss/align-items]
                center
`;
