/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the direction to set on the selection of this guest name
        input. This value is not a representation of current selection, but
        an instruction to set a new selection. Must be set together with
        'doSetSelectionEndOnGuestNameInput' and 'doSetSelectionStartOnGuestNameInput'
        to have an effect.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            doSetSelectionDirectionOnGuestNameInput
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            attr
        [Field/target]
            Boolean
`;
