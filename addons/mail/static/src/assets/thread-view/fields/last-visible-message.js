/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Most recent message in this ThreadView that has been shown to the
        current partner in the currently displayed thread cache.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            lastVisibleMessage
        [Field/model]
            ThreadView
        [Field/type]
            one
        [Field/target]
            Message
`;
