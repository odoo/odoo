/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            connectionStateIcon
        [Element/model]
            RtcCallParticipantCardComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-exclamation-triangle
        [web.Element/style]
            [web.scss/color]
                {scss/theme-color}
                    warning
`;
