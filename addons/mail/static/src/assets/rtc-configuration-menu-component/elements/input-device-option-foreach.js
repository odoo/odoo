/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            inputDeviceOptionForeach
        [Element/model]
            RtcConfigurationMenuComponent
        [Field/target]
            RtcConfigurationMenuComponent:inputDeviceOption
        [RtcConfigurationMenuComponent:inputDeviceOption/device]
            @field
            .{Foreach/get}
                device
        [Record/models]
            Foreach
        [Foreach/collection]
            @record
            .{RtcConfigurationMenuComponent/userDevices}
        [Foreach/as]
            device
        [Element/key]
            @field
            .{Foreach/get}
                device
            .{Device/index}
`;
