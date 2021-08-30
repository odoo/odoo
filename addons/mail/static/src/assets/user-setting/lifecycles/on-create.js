/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Lifecycle
        [Lifecycle/name]
            onCreate
        [Lifecycle/model]
            UserSetting
        [Lifecycle/behavior]
            {UserSetting/loadLocalSettings}
                @record
`;
