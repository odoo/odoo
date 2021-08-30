/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isBelow
        [Field/model]
            ComposerSuggestionListComponent
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
