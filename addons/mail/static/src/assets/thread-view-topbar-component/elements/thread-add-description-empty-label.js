/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            threadAddDescriptionEmptyLabel
        [Element/model]
            ThreadViewTopbarComponent
        [Element/isPresent]
            @record
            .{ThreadViewTopbarComponent/threadViewTopbar}
            .{ThreadViewTopbar/thread}
            .{&}
                {Env/isCurrentUserGuest}
                .{isFalsy}
            .{&}
                @record
                .{ThreadViewTopbarComponent/threadViewTopbar}
                .{ThreadViewTopbar/thread}
                .{Thread/isChannelDescriptionChangeable}
            .{&}
                @record
                .{ThreadViewTopbarComponent/threadViewTopbar}
                .{ThreadViewTopbar/isEditingThreadDescription}
                .{isFalsy}
            .{&}
                @record
                .{ThreadViewTopbarComponent/threadViewTopbar}
                .{ThreadViewTopbar/description}
                .{isFalsy}
        [web.Element/class]
            text-truncate
        [Element/onClick]
            @record
            .{ThreadViewTopbarComponent/threadViewTopbar}
            .{ThreadViewTopbar/onClickTopbarThreadDescription}
                @ev
        [web.Element/textContent]
            {Locale/text}
                Add a description
        [web.Element/style]
            [web.scss/color]
                {scss/gray}
                    400
            [web.scss/cursor]
                pointer
            {if}
                @field
                .{web.Element/isHover}
            .{then}
                [web.scss/color]
                    {scss/gray}
                        900
`;