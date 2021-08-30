/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the position inside textInputContent of the suggestion
        delimiter currently in consideration. Useful if the delimiter char
        appears multiple times in the content.
        Note: the position is 0 based so it's important to compare to
        'undefined' when checking for the absence of a value.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            suggestionDelimiterPosition
        [Field/model]
            ComposerView
        [Field/type]
            attr
        [Field/target]
            Integer
`;
