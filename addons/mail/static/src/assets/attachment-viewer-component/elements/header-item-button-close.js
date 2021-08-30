/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            headerItemButtonClose
        [Element/model]
            AttachmentViewerComponent
        [Record/models]
            AttachmentViewerComponent/headerItem
            AttachmentViewerComponent/headerItemButton
        [Element/onClick]
            {AttachmentViewerComponent/_close}
                @record
        [web.Element/role]
            button
        [web.Element/title]
            {Locale/text}
                Close (Esc)
        [web.Element/aria-label]
            {Locale/text}
                Close
        [web.Element/style]
            [web.scss/cursor]
                pointer
            [web.scss/font-size]
                1.3
                rem
`;
