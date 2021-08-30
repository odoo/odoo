/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            volumeMenuAnchorPopover
        [Element/model]
            RtcCallParticipantCardComponent
        [Record/models]
            PopoverComponent
        [web.Element/style]
            [web.scss/position]
                absolute
            [web.scss/bottom]
                0
            [web.scss/left]
                50%
`;
