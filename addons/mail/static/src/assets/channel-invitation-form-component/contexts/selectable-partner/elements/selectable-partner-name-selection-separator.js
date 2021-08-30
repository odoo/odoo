/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            selectablePartnerNameSelectionSeparator
        [Element/model]
            ChannelInvitationFormComponent:selectablePartner
        [web.Element/class]
            flex-grow-1
            flex-shrink-0
        [web.Element/style]
            [web.scss/min-width]
                {scss/map-get}
                    {scss/$spacers}
                    2
`;
