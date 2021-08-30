/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            selectablePartnerAvatarNameSeparator
        [Element/model]
            ChannelInvitationFormComponent:selectablePartner
        [web.Element/style]
            [web.scss/min-width]
                {scss/map-get}
                    {scss/$spacers}
                    2
`;
