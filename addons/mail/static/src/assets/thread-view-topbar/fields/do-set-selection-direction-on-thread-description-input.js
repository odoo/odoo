/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the direction to set on the selection of this thread description
        input. This value is not a representation of current selection, but
        an instruction to set a new selection. Must be set together with
        'doSetSelectionEndOnThreadDescriptionInput' and 'doSetSelectionStartOnThreadDescriptionInput'
        to have an effect.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            doSetSelectionDirectionOnThreadDescriptionInput
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            attr
        [Field/target]
            Boolean
`;
