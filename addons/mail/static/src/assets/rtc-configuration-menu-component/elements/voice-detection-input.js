/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            voiceDetectionInput
        [Element/model]
            RtcConfigurationMenuComponent
        [Record/models]
            RtcConfigurationMenuComponent/inputGroupInput
        [web.Element/min]
            0.001
        [web.Element/max]
            1
        [web.Element/step]
            0.001
        [web.Element/value]
            {Env/userSetting}
            .{UserSetting/voiceActivationThreshold}
        [Element/onChange]
            {RtcConfigurationMenuComponent/_onChangeThreshold}
                [0]
                    @record
                [1]
                    @ev
`;
