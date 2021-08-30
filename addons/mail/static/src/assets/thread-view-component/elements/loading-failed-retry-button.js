/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            loadingFailedRetryButton
        [Element/model]
            ThreadViewComponent
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-link
        [Element/onClick]
            {Record/update}
                [0]
                    @record
                    .{ThreadViewComponent/threadView}
                    .{ThreadView/threadCache}
                [1]
                    [ThreadCache/hasLoadingFailed]
                        false
        [web.Element/textContent]
            {Locale/text}
                Click here to retry
`;
