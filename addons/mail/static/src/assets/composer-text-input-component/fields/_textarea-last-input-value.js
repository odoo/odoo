/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Last content of textarea from input event.

        Useful to determine whether the current partner is typing something.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            _textareaLastInputValue
        [Field/model]
            ComposerTextInputComponent
        [Field/type]
            attr
        [Field/target]
            String
`;
