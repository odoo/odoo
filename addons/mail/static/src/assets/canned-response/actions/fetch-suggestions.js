/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Fetches canned responses matching the given search term to extend the
        JS knowledge and to update the suggestion list accordingly.

        In practice all canned responses are already fetched at init so this
        method does nothing.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            CannedResponse/fetchSuggestions
        [Action/params]
            searchTerm
            [thread]
                [description]
                    prioritize and/or restrict result in the context of
                    given thread
`;
