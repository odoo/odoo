/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ModelAddon
        [ModelAddon/feature]
            website_slides
        [ModelAddon/model]
            ActivityComponent
        [ModelAddon/template]
            tools
                grantAccessButton
                    grantAccessButtonIcon
                    grantAccessButtonLabel
                refuseAccessButton
                    refuseAccessButtonIcon
                    refuseAccessButtonLabel
`;
