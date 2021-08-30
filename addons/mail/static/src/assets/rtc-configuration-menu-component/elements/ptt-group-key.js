/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            pttGroupKey
        [Element/model]
            RtcConfigurationMenuComponent
        [web.Element/tag]
            span
        [Element/isPresent]
            {Env/userSetting}
            .{UserSetting/pushToTalkKey}
        [web.Element/textContent]
            {UserSetting/pushToTalkKeyToString}
                {Env/userSetting}
        [web.Element/style]
            [web.scss/padding-left]
                {scss/map-get}
                    {scss/$spacers}
                    3
            [web.scss/padding-right]
                {scss/map-get}
                    {scss/$spacers}
                    3
            [web.scss/margin-left]
                {scss/map-get}
                    {scss/$spacers}
                    1
            [web.scss/font-size]
                1.4
                em
            [web.scss/font-weight]
                bold
            [web.scss/border-radius]
                3px
            [web.scss/border]
                2px
                solid
                {scss/$o-brand-primary}
            {if}
                {Env/userSetting}
                .{UserSetting/rtcConfigurationMenu}
                .{RtcConfigurationMenu/isRegisteringKey}
            .{then}
                [web.scss/border-color]
                    {scss/theme-color}
                        danger
`;
