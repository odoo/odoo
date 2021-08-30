/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonNavigationPrevious
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
            {AttachmentViewerComponent/_previous}
                @record
        [web.Element/title]
            {Locale/text}
                Previous (Left-Arrow)
        [web.Element/style]
            [web.scss/left]
                15
                px
            {scss/selector}
                [0]
                    > .fa
                [1]
                    [web.scss/margin]
                        1px
                        1px
                        0
                        0
                        {Dev/comment}
                            not correctly centered for some reasons
`;
