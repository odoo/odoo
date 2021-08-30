/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            header
        [Element/model]
            AttachmentViewerComponent
        [Element/onClick]
            {Dev/comment}
                Stop propagation of event to prevent closing the dialog.
            {web.Event/stopPropagation}
                @ev
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/height]
                {scss/$o-navbar-height}
            [web.scss/width]
                100%
            [web.scss/background-color]
                {scss/rgba}
                    {scss/$black}
                    0.7
            [web.scss/color]
                {scss/gray}
                    400
`;
