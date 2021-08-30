/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            partnerImStatusIcon
        [Element/model]
            NotificationRequestComponent
        [Field/target]
            PartnerImStatusIconComponent
        [Record/models]
            NotificationListItemComponent/partnerImStatusIcon
        [PartnerImStatusIconComponent/partner]
            {Env/partnerRoot}
`;
