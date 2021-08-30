/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            volumeSettingsTimeouts
        [Field/model]
            UserSetting
        [Field/type]
            attr
        [Field/target]
            Dict
`;
