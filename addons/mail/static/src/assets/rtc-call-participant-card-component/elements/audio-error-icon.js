/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            audioErrorIcon
        [Element/model]
            RtcCallParticipantCardComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-exclamation-triangle
`;
