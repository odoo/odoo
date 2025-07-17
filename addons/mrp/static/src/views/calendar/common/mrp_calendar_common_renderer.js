import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { renderToFragment } from "@web/core/utils/render";

export class MRPCalendarCommonRenderer extends CalendarCommonRenderer {
    static eventTemplate = "mrp.CalendarCommonRenderer.event"

    /**
     * @override
     */
    onEventContent({ event }) {
        const record = this.props.model.records[event.id];
        if (record) {
            const fragment = renderToFragment(this.constructor.eventTemplate, {
                ...record,
                product_id: record.rawRecord.product_id[1],
                product_qty: record.rawRecord.product_qty,
                product_uom:record.rawRecord.product_uom_id[1]
            });
            return { domNodes: fragment.children };
        }
        return true;
    }
}
