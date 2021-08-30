/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ModelAddon
        [ModelAddon/feature]
            hr
        [ModelAddon/model]
            User
        [ModelAddon/fields]
            employee
`;
