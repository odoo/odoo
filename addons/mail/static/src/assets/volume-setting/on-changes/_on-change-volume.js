/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            onChange
        [onChange/name]
            _onChangeVolume
        [onChange/model]
            VolumeSetting
        [onChange/dependencies]
            VolumeSetting/volume
        [onChange/behavior]
            {if}
                @record
                .{VolumeSetting/partner}
            .{then}
                :rtcSessions
                    @record
                    .{VolumeSetting/partner}
                    .{Partner/rtcSessions}
            .{elif}
                @record
                .{VolumeSetting/guest}
            .{then}
                :rtcSessions
                    @record
                    .{VolumeSetting/guest}
                    .{Guest/rtcSessions}
            .{else}
                {break}
            {foreach}
                @rtcSessions
            .{as}
                rtcSession
            .{do}
                {if}
                    @rtcSession
                    .{RTCSession/audioElement}
                .{then}
                    {Record/update}
                        [0]
                            @rtcSession
                            .{RTCSession/audioElement}
                        [1]
                            [AudioElement/volume]
                                @record
                                .{VolumeSetting/volume}
`;
