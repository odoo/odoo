/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            loadingFailed
        [Element/model]
            ThreadViewComponent
        [Element/isPresent]
            @record
            .{ThreadViewComponent/threadView}
            .{&}
                @record
                .{ThreadViewComponent/threadView}
                .{ThreadView/threadCache}
                .{ThreadCache/hasLoadingFailed}
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex]
                1
                1
                auto
            [web.scss/align-items]
                center
            [web.scss/justify-content]
                center
            [web.scss/flex-direction]
                column
`;
