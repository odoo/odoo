/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            detailsCreationDatetime
        [Element/model]
            ActivityComponent
        [web.Element/tag]
            span
        [web.Element/textContent]
            @record
            .{ActivityComponent/activityView}
            .{ActivityView/formattedCreateDatetime}
            .{+}
                {Locale/text}
                    , 
                    .{+}
                        {if}
                            {Env/isMobile}
                        .{then}
                            <br/>
                    .{+}
                        by
`;
