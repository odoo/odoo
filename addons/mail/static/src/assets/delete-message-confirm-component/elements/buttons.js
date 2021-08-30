/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttons
        [Element/model]
            DeleteMessageConfirmDialogComponent
        [web.Element/class]
            mx-3
            mb-3
`;
