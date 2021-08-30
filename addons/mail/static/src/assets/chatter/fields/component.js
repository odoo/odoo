/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the OWL Chatter component of this chatter.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            component
        [Field/model]
            Chatter
        [Field/type]
            one
        [Field/target]
            ChatterComponent
`;
