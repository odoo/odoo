/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            loadingIcon
        [Element/model]
            AttachmentViewerComponent
        [web.Element/tag]
            i
        [web.Element/class]
            fa
            fa-3x
            fa-circle-o-notch
            fa-fw
            fa-spin
        [web.Element/role]
            img
        [web.Element/title]
            {Locale/text}
                Loading
`;
