/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Backup of the feedback content of an activity to be marked as done in the popover.
        Feature-specific to restoring the feedback content when component is re-mounted.
        In all other cases, this field value should not be trusted.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            feedbackBackup
        [Field/model]
            Activity
        [Field/type]
            attr
`;
