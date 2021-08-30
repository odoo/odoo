/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            onChange
        [onChange/name]
            RtcCallViewer/_onChangeRtcChannel
        [onChange/model]
            RtcCallViewer
        [onChange/dependencies]
            RtcCallViewer/threadView
                ThreadView/thread
                    Thread/mailRtc
        [onChange/behavior]
            {RtcCallViewer/deactivateFullScreen}
                @record
            {Record/update}
                [0]
                    @record
                [1]
                    [RtcCallViewer/filterVideoGrid]
                        false
`;
