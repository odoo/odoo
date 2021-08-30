/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Lifecycle
        [Lifecycle/name]
            onDelete
        [Lifecycle/model]
            ComposerView
        [Lifecycle/behavior]
            {Dev/comment}
                Clears the mention queue on deleting the record to prevent
                unnecessary RPC.
            {Record/update}
                [0]
                    @record
                [1]
                    [ComposerView/_nextMentionRpcFunction]
                        {Record/empty}
`;