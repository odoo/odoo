/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Event handler for clicking thread in discuss app.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/onClick
        [Action/params]
            record
                [type]
                    Thread
        [Action/behavior]
            {Thread/open}
                @record
`;
