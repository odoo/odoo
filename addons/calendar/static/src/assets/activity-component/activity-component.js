/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ModelAddon
        [ModelAddon/feature]
            calendar
        [ModelAddon/model]
            ActivityComponent
        [ModelAddon/template]
            editButton
            rescheduleButton
                rescheduleButtonIcon
                rescheduleButtonLabel
        [ModelAddon/elementAddons]
            cancelButton
            editButton
`;
