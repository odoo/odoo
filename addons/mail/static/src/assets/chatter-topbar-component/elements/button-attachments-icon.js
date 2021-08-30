/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonAttachmentsIcon
        [Element/model]
            ChatterTopbarComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-paperclip
`;
