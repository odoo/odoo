/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            icon
        [Element/model]
            DropZoneComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-download
`;
