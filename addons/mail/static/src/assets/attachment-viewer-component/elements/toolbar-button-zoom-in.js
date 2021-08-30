/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            toolbarButtonZoomIn
        [Element/model]
            AttachmentViewerComponent
        [Record/models]
            AttachmentViewerComponent/toolbarButton
        [Element/onClick]
            {web.Event/stopPropagation}
                @ev
            {AttachmentViewerComponent/_zoomIn}
                @record
        [web.Element/title]
            {Locale/text}
                Zoom In (+)
        [web.Element/role]
            button
`;
