/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            threadDescriptionSeparator
        [Element/model]
            ThreadViewTopbarComponent
        [Element/isPresent]
            @record
            .{ThreadViewTopbarComponent/threadViewTopbar}
            .{ThreadViewTopbar/thread}
            .{&}
                @record
                .{ThreadViewTopbarComponent/threadViewTopbar}
                .{ThreadViewTopbar/thread}
                .{Thread/isChannelDescriptionChangeable}
        [web.Element/class]
            flex-shrink-0
            mx-2
        [web.Element/style]
            [web.scss/width]
                {scss/$border-width}
            [web.scss/height]
                {scss/$font-size-sm}
            [web.scss/background-color]
                {scss/$border-color}
`;