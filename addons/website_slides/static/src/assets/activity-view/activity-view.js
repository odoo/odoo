/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ModelAddon
        [ModelAddon/feature]
            website_slides
        [ModelAddon/model]
            ActivityView
        [ModelAddon/actions]
            ActivityView/onGrantAccess
            ActivityView/onRefuseAccess
`;
