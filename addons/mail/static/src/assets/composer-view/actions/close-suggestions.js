/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Closes the suggestion list.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ComposerView/closeSuggestions
        [Action/params]
            record
                [type]
                    ComposerView
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [ComposerView/suggestionDelimiterPosition]
                        {Record/empty}
`;
