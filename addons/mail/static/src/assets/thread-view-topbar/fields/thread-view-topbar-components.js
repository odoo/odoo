/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the thread view managing this top bar.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadViewTopbarComponents
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            many
        [Field/target]
            ThreadViewTopbarComponent
        Field/inverse]
            ThreadViewTopbarComponent/threadViewTopbar
`;
