/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether the currently active suggestion should be scrolled
        into view.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasToScrollToActiveSuggestion
        [Field/model]
            ComposerView
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
