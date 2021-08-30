/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        When a new image is displayed, show a spinner until it is loaded.
    {Lifecycle}
        [Lifecycle/name]
            onPatched
        [Lifecycle/model]
            AttachmentViewerComponent
        [Lifecycle/behavior]
            {AttachmentViewerComponent/_handleImageLoad}
                @record
            {AttachmentViewerComponent/_hideUnwantedPdfJsButtons}
                @record
`;
