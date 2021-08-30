/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ModelAddon
        [ModelAddon/feature]
            calendar
        [ModelAddon/model]
            ActivityView
        [ModelAddon/actionAddons]
            ActivityView/onClickCancel
`;
