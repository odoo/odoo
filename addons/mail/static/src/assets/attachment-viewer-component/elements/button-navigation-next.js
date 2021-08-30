/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonNavigationNext
        [Element/model]
            AttachmentViewerComponent
        [Record/models]
            AttachmentViewerComponent/buttonNavigation
        [web.Element/role]
            button
        [Element/isPresent]
            @record
            .{AttachmentViewerComponent/record}
            .{AttachmentViewer/attachments}
            .{Collection/length}
            .{>}
                1
        [Element/onClick]
            {web.Event/stopPropagation}
                @ev
            {AttachmentViewerComponent/_next}
                @record
        [web.Element/title]
            {Locale/text}
                Next (Right-Arrow)
        [web.Element/style]
            [web.scss/right]
                15
                px
            {scss/selector}
                [0]
                    > .fa
                [1]
                    [web.scss/margin]
                        1px
                        0
                        0
                        1px
                        {Dev/comment}
                            not correctly centered for some reasons
`;
