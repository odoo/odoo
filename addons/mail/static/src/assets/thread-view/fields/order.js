/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the order mode of the messages on this thread view.
        Either 'asc', or 'desc'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            order
        [Field/model]
            ThreadView
        [Field/type]
            attr
        [Field/related]
            ThreadView/threadViewer
            ThreadViewer/order
`;
