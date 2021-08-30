/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            inputDeviceOption
        [Element/model]
            RtcConfigurationMenuComponent:inputDeviceOption
        [web.Element/tag]
            option
        [Element/isPresent]
            @record
            .{inputDeviceOption/device}
            .{Device/kind}
            .{=}
                audioinput
        [web.Element/value]
            @record
            .{inputDeviceOption/device}
            .{Device/deviceId}
        [web.Element/textContent]
            @record
            .{inputDeviceOption/device}
            .{Device/label}
`;
