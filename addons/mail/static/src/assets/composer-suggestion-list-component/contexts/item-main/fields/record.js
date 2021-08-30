/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            record
        [Field/model]
            ComposerSuggestionListComponent:itemMain
        [Field/type]
            one
        [Field/target]
            Record
        [Field/isRequired]
            true
`;
