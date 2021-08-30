/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            device
        [Field/model]
            RtcConfigurationMenuComponent:inputDeviceOption
        [Field/type]
            one
        [Field/target]
            Device
        [Field/isRequired]
            true
`;
