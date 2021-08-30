/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            attachment
        [Element/model]
            AttachmentListComponent
        [web.Element/class]
            my-1
            me-1
            mw-100
`;
