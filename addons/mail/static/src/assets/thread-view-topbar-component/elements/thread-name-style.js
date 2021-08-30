/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            threadNameStyle
        [Element/model]
            ThreadViewTopbarComponent
        [web.Element/style]
            [web.scss/max-width]
                {scss/map-get}
                    {scss/$sizes}
                    75
            {if}
                @record
                .{ThreadViewTopbarComponent/threadViewTopbar}
                .{ThreadViewTopbar/isMouseOverThreadName}
                .{&}
                    {Env/isCurrentUserGuest}
                    .{isFalsy}
            .{then}
                [web.scss/background-color]
                    {scss/$white}
                [web.scss/border-color]
                    {scss/$border-color}
            {if}
                @record
                .{ThreadViewTopbarComponent/threadViewTopbar}
                .{ThreadViewTopbar/isMouseOverThreadName}
                .{isFalsy}
                .{|}
                    {Env/isCurrentUserGuest}
            .{then}
                [web.scss/border-color]
                    transparent
                    {Dev/comment}
                        presence of border even if invisible to prevent flicker
`;