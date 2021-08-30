/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether each "read more" is opened or closed. The keys are
        index, which is determined by their order of appearance in the DOM.
        If body changes so that "read more" count is different, their default
        value will be "wrong" at the next render but this is an acceptable
        limitation. It's more important to save the state correctly in a
        typical non-changing situation.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            _isReadMoreByIndex
        [Field/model]
            MessageViewComponent
        [Field/type]
            attr
        [Field/target]
            Map
`;
