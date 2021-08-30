/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            RtcConfigurationMenu
        [Model/fields]
            device
            isOpen
            isRegisteringKey
            userSetting
        [Model/id]
            RtcConfigurationMenu/userSetting
        [Model/actions]
            RtcConfigurationMenu/_onKeydown
            RtcConfigurationMenu/_onKeyup
            RtcConfigurationMenu/onClickRegisterKeyButton
            RtcConfigurationMenu/toggle
`;
