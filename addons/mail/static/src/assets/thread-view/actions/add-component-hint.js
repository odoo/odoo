/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        This function register a hint for the component related to this
        record. Hints are information on changes around this viewer that
        make require adjustment on the component. For instance, if this
        ThreadView initiated a thread cache load and it now has become
        loaded, then it may need to auto-scroll to last message.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadView/addComponentHint
        [Action/params]
            threadView
                [type]
                    ThreadView
            hintType
                [type]
                    String
                [description]
                    name of the hint. Used to determine what's the broad type
                    of adjustement the component has to do.
            hintData
                [description]
                    data of the hint. Used to fine-tune adjustments on the
                    component.
        [Action/behavior]
            :hint
                {Record/insert}
                    [Record/models]
                        Hint
                    [Hint/data]
                        @hintData
                    [Hint/type]
                        @hintType
            {Record/update}
                [0]
                    @threadView
                [1]
                    [ThreadView/componentHintList]
                        {Field/add}
                            @hint
`;
