/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Get an object which is passed to FileUploader component to be used when
        creating attachment.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ComposerViewComponent/newAttachmentExtraData
        [Action/params]
            record
        [Action/behavior]
            {Record/insert}
                [Record/models]
                    Dict
                [composers]
                    @record
                    .{ComposerViewComponent/composerView}
                    .{ComposerView/composer}
`;
