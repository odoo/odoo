/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            pttKey
        [Element/model]
            RtcConfigurationMenuComponent
        [Record/models]
            RtcConfigurationMenuComponent/option
        [Element/isPresent]
            {Env/userSetting}
            .{UserSetting/usePushToTalk}
`;
