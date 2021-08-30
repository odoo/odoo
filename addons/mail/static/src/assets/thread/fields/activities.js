/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the 'Activity' that belong to 'this', assuming 'this'
        has activities (@see hasActivities).
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            activities
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            Activity
        [Field/inverse]
            Activity/thread
`;
