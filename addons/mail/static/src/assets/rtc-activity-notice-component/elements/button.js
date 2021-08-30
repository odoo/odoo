/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            button
        [Element/model]
            RtcActivityNoticeComponent
        [Element/isPresent]
            {Rtc/channel}
        [web.Element/class]
            px-3
            user-select-none
            dropdown-toggle
            o-no-caret
            o-dropdown--narrow
        [web.Element/tag]
            a
        [web.Element/role]
            button
        [web.Element/title]
            {String/sprintf}
                [0]
                    {Locale/text}
                        Open conference: %s
                [1]
                    {Rtc/channel}
                    .{Thread/displayName}
        [Element/onClick]
            {RtcActivityNoticeComponent/onClick}
                [0]
                    @record
                [1]
                    @ev
        [web.Element/style]
            [web.scss/box-shadow]
                0
                {web.scss/$border-width}
                .{*}
                    2
                0
                {web.scss/$border-width $o-navbar-entry-bg--hover}
`;
