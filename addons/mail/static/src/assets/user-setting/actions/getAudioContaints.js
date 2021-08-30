/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            UserSetting/getAudioContaints
        [Action/params]
            record
                [type]
                    UserSetting
        [Action/returns]
            Object
                [description]
                    MediaTrackConstraints
        [Action/behavior]
            :constraints
                {Record/insert}
                    [Record/models]
                        Object
                    [echoCancellation]
                        true
                    [noiseSuppression]
                        true
            {if}
                @record
                .{UserSetting/audioInputDeviceId}
            .{then}
                {Record/update}
                    [0]
                        @constraints
                    [1]
                        [deviceId]
                            @record
                            .{UserSetting/audioInputDeviceId}
            @constraints
`;
