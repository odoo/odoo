/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The volume of the audio played from this session.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            volume
        [Field/model]
            RtcSession
        [Field/type]
            attr
        [Field/target]
            Float
        [Field/default]
            0.5
        [Field/compute]
            {if}
                @record
                .{RtcSession/partner}
                .{&}
                    @record
                    .{RtcSession/partner}
                    .{Partner/volumeSetting}
            .{then}
                @record
                .{RtcSession/partner}
                .{Partner/volumeSetting}
                .{VolumeSetting/volume}
            .{elif}
                @record
                .{RtcSession/guest}
                .{&}
                    @record
                    .{RtcSession/guest}
                    .{Guest/volumeSetting}
            .{then}
                @record
                .{RtcSession/guest}
                .{Guest/volumeSetting}
                .{VolumeSetting/volume}
            .{elif}
                @record
                .{RtcSession/audioElement}
            .{then}
                @record
                .{RtcSession/audioElement}
                .{Audio/volume}
`;
