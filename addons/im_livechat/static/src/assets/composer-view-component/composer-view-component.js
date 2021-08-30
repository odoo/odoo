/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ModelAddon
        [ModelAddon/feature]
            hr_holidays
        [ModelAddon/model]
            ComposerViewComponent
        [ModelAddon/elementAddons]
            buttonAttachment
`;
