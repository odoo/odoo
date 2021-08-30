/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            partnerInfoText
        [Element/model]
            RtcInvitationCardComponent
        [web.Element/tag]
            span
        [web.Element/textContent]
            {Locale/text}
                Incoming Call...
        [web.Element/style]
            [web.scss/font-style]
                italic
            [web.scss/opacity]
                0.9
`;
