/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            dashedLineEnd
        [Element/model]
            AttachmentBoxComponent
        [web.Element/tag]
            hr
        [Record/models]
            AttachmentBoxComponent/dashedLine
`;
