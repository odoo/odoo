/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        List of component hints. Hints contain information that help
        components make UI/UX decisions based on their UI state.
        For instance, on receiving new messages and the last message
        is visible, it should auto-scroll to this new last message.

        Format of a component hint:

        {
            type: {string} the name of the component hint. Useful
                            for components to dispatch behaviour
                            based on its type.
            data: {Object} data related to the component hint.
                            For instance, if hint suggests to scroll
                            to a certain message, data may contain
                            message id.
        }
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            componentHintList
        [Field/model]
            ThreadView
        [Field/type]
            many
        [Field/target]
            Hint
`;
