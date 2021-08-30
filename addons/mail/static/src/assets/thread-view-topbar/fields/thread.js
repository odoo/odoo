/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the thread that is displayed by this top bar.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            thread
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            one
        [Field/target]
            Thread
        [Field/related]
            'ThreadView.thread'
`;
