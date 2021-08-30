/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            dashedLine
        [Element/model]
            AttachmentBoxComponent
        [web.Element/class]
            flex-grow-1
        [web.Element/style]
            [web.scss/border-top]
                {web.scss/border-width}
                dashed
                {web.scss/border-color}
`;
