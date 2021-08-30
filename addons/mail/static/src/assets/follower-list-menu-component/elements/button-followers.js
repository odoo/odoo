/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonFollowers
        [Element/model]
            FollowerListMenuComponent
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-link
        [Record/models]
            Focusable
        [web.Element/isDisabled]
            @record
            .{FollowerListMenuComponent/isDisabled}
        [Element/onClick]
            {Record/update}
                [0]
                    @record
                [1]
                    [FollowerListMenuComponent/isDropdownOpen]
                        @record
                        .{FollowerListMenuComponent/isDropdownOpen}
                        .{isFalsy}
        [web.Element/title]
            {Locale/text}
                Show Followers
        [web.Element/style]
            {if}
                @field
                .{web.Element/isFocused}
            .{then}
                [web.scss/background-color]
                    {scss/gray}
                        200
`;
