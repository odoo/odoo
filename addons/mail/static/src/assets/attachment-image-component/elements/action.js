/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            action
        [Element/model]
            AttachmentImageComponent
        [web.Element/style]
`;
