/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            micIcon
        [Element/model]
            RtcCallParticipantCardComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-microphone-slash
`;
