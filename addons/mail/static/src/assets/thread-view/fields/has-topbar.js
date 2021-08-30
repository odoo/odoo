/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether this thread view has a top bar.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasTopbar
        [Field/model]
            ThreadView
        [Field/type]
            attr
        [Field/related]
            ThreadView/threadviewer
            ThreadViewer/hasTopbar
`;
