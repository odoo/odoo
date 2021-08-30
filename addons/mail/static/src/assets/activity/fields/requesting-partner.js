/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines that an activity is linked to a requesting partner or not.
        It will be used notably in website slides to know who triggered the
        "request access" activity.
        Also, be useful when the assigned user is different from the
        "source" or "requesting" partner.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            requestingPartner
        [Field/model]
            Activity
        [Field/type]
            one
        [Field/target]
            Partner
`;
