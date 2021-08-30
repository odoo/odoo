/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            loading
        [Element/model]
            ThreadViewComponent
        [Element/isPresent]
            @record
            .{ThreadViewComponent/threadView}
            .{ThreadView/isLoading}
            .{&}
                @record
                .{ThreadViewComponent/threadView}
                .{ThreadView/threadCache}
                .{ThreadCache/isLoaded}
                .{isFalsy}
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/align-self]
                center
            [web.scss/flex]
                1
                1
                auto
            [web.scss/align-items]
                center
`;
