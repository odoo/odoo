/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        DeviceId of the audio input selected by the user
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            audioInputDeviceId
        [Field/model]
            UserSetting
        [Field/type]
            attr
        [Field/target]
            String
`;
