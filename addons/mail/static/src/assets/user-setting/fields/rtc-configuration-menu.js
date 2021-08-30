/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Model for the component with the controls for RTC related settings.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            rtcConfigurationMenu
        [Field/model]
            UserSetting
        [Field/type]
            one
        [Field/target]
            RtcConfigurationMenu
        [Field/isCausal]
            true
        [Field/isRequired]
            true
        [Field/inverse]
            RtcConfigurationMenu/userSetting
        [Field/default]
            {Record/insert}
                [Record/models]
                    RtcConfigurationMenu
`;
