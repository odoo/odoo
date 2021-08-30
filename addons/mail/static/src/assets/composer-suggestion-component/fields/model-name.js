/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            modelName
        [Field/model]
            ComposerSuggestionComponent
        [Field/type]
            attr
        [Field/target]
            String
        [Field/isRequired]
            true
`;
