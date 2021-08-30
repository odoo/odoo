/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the direction to set on the selection of this thread name
        input. This value is not a representation of current selection, but
        an instruction to set a new selection. Must be set together with
        'doSetSelectionEndOnThreadNameInput' and 'doSetSelectionStartOnThreadNameInput'
        to have an effect.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            doSetSelectionDirectionOnThreadNameInput
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            attr
        [Field/target]
            Boolean
`;
