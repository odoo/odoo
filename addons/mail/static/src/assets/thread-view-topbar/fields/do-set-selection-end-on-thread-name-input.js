/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the ending position where to place the selection on this
        thread name input (zero-based index). This value is not a
        representation of current selection, but an instruction to set a new
        selection. Must be set together with 'doSetSelectionDirectionOnThreadNameInput'
        and 'doSetSelectionStartOnThreadNameInput' to have an effect.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            doSetSelectionEndOnThreadNameInput
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            attr
        [Field/target]
            Boolean
`;
