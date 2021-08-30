/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            pttRegisteringButtonIcon
        [Element/model]
            RtcConfigurationMenuComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-2x
            {if}
                {Env/userSetting}
                .{UserSetting/rtcConfigurationMenu}
                .{RtcConfigurationMenu/isRegisteringKey}
            .{then}
                fa-times-circle
            .{else}
                fa-keyboard-o
        [web.Element/title]
            {if}
                {Env/userSetting}
                .{UserSetting/rtcConfigurationMenu}
                .{RtcConfigurationMenu/isRegisteringKey}
            .{then}
                {Locale/text}
                    Cancel
            .{else}
                {Locale/text}
                    Register a new key
        [web.Element/aria-label]
            {if}
                {Env/userSetting}
                .{UserSetting/rtcConfigurationMenu}
                .{RtcConfigurationMenu/isRegisteringKey}
            .{then}
                {Locale/text}
                    Cancel
            .{else}
                {Locale/text}
                    Register a new key
`;
