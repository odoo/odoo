/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            voiceDetectionValue
        [Element/model]
            RtcConfigurationMenuComponent
        [Record/models]
            RtcConfigurationMenuComponent/inputGroupValue
        [web.Element/textContent]
            {Env/userSetting}
            .{UserSetting/voiceActivationThreshold}
`;
