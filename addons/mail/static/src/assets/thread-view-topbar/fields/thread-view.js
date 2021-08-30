/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the thread view managing this top bar.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadView
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            one
        [Field/target]
            ThreadView
        [Field/inverse]
            ThreadView/topbar
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
`;
