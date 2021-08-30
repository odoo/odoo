/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/_onKeydown
        [Action/params]
            ev
                [type]
                    KeyboardEvent
        [Action/behavior]
            {if}
                {Rtc/channel}
                .{isFalsy}
            .{then}
                {break}
            {if}
                {Env/userSetting}
                .{UserSetting/usePushToTalk}
                .{isFalsy}
                .{|}
                    {Env/userSetting}
                    .{UserSetting/isPushToTalkKey}
                        @ev
                    .{isFalsy}
            .{then}
                {break}
            {if}
                {Rtc/currentRtcSession}
                .{RtcSession/isMute}
            .{then}
                {break}
            {if}
                {Env/userSetting}
                .{UserSetting/rtcConfigurationMenu}
                .{RtcConfigurationMenu/isRegisteringKey}
            .{then}
                {break}
            {if}
                {Rtc/_pushToTalkTimeoutId}
            .{then}
                {web.Browser/clearTimeout}
                    {Rtc/_pushToTalkTimeoutId}
            {if}
                {Rtc/currentRtcSession}
                .{RtcSession/isTalking}
                .{isFalsy}
            .{then}
                {SoundEffect/play}
                    {SoundEffects/pushToTalkOn}
                {Rtc/_setSoundBroadcast}
                    true
`;
