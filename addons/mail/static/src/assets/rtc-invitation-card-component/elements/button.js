/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            button
        [Element/model]
            RtcInvitationCardComponent
        [web.Element/style]
            [web.scss/padding]
                {scss/map-get}
                    {scss/$spacers}
                    2
            [web.scss/border-radius]
                100%
            [web.scss/cursor]
                pointer
            [web.scss/user-select]
                none
            [web.scss/border]
                none
`;
