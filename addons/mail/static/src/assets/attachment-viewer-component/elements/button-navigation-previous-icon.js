/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonNavigationPreviousIcon
        [Element/model]
            AttachmentViewerComponent
        [web.Element/tag]
            span
        [web.Element/class]
            fa
            fa-chevron-left
        [web.Element/role]
            img
`;
