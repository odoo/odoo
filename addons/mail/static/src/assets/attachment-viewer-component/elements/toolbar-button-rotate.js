/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            toolbarButtonRotate
        [Element/model]
            AttachmentViewerComponent
        [Record/models]
            AttachmentViewerComponent/toolbarButton
        [Element/onClick]
            {web.Event/stopPropagation}
                @ev
            {AttachmentViewerComponent/_rotate}
                @record
        [web.Element/title]
            {Locale/text}
                Rotate (r)
        [web.Element/role]
            button
`;
