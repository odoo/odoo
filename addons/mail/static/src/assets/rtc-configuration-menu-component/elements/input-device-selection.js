/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            inputDeviceSelection
        [Element/model]
            RtcConfigurationMenuComponent
        [web.Element/tag]
            select
        [web.Element/name]
            inputDevice
        [web.Element/value]
            {Env/userSetting}
            .{UserSetting/audioInputDeviceId}
        [Element/onChange]
            {RtcConfigurationMenuComponent/onChangeSelectAudioInput}
                [0]
                    @record
                [1]
                    @ev
        [web.Element/style]
            [web.scss/padding]
                {scss/map-get}
                    {scss/$spacers}
                    1
            [web.scss/padding-right]
                {scss/map-get}
                    {scss/$spacers}
                    3
`;
