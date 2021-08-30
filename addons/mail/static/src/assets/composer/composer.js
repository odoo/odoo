/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            Composer
        [Model/fields]
            activeThread
            attachments
            canPostMessage
            composerViews
            hasUploadingAttachment
            isLastStateChangeProgrammatic
            isLog
            isPostingMessage
            mentionedChannels
            mentionedPartners
            messageViewInEditing
            recipients
            textInputContent
            textInputCursorEnd
            textInputCursorStart
            textInputSelectionDirection
            thread
        [Model/id]
            Composer/thread
            .{|}
                Composer/messageViewInEditing
        [Model/actions]
            Composer/_reset
            Composer/detectSuggestionDelimiter
`;
