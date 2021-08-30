/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ComposerTextInputComponent
        [Model/fields]
            _textareaLastInputValue
            composerView
            hasMentionSuggestionsBelowPosition
            isCompact
        [Model/template]
            root
                suggestionList
                textarea
                {Dev/comment}
                    Invisible mirrored textarea.
                    Used to compute the composer height based on the text content.
                mirroredTextarea
        [Model/actions]
            ComposerTextInputComponent/_updateHeight
            ComposerTextInputComponent/saveStateInStore
        [Model/lifecycles]
            onUpdate
`;
