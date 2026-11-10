import { t, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField, x2ManyFieldProps } from "@web/views/fields/x2many/x2many_field";
import { Domain } from "@web/core/domain";

export class ResourceCalendarAttendanceFilteredOne2Many extends X2ManyField {
    props = useProps({
        ...x2ManyFieldProps,
        domainFilter: t.instanceOf(Domain),
    });

    /**
     * @override
     */
    get rendererProps() {
        const props = super.rendererProps;
        const list = this.list;

        if (!this.props.domainFilter || (!list.records && !list._cache)) {
            return list;
        }

        if (list.records) {
            const records = list.records.filter((r) => this.props.domainFilter.contains(r.data));
            props.list = new Proxy(list, {
                get(target, property) {
                    if (property === "records") {
                        return records;
                    }
                    const value = Reflect.get(target, property, target);
                    return typeof value === "function" ? value.bind(target) : value;
                },
            });
        }
        return props;
    }
}

export const calendarOne2Many = {
    ...x2ManyField,
    component: ResourceCalendarAttendanceFilteredOne2Many,
    supportedAttributes: [
        {
            label: "Domain to filter the list",
            name: "domain_filter",
            type: "string",
        },
    ],
    extractProps: (staticInfo, dynamicInfo) => ({
        ...x2ManyField.extractProps(staticInfo, dynamicInfo),
        domainFilter: new Domain(staticInfo.attrs.domain_filter),
    }),
};

registry.category("fields").add("resource_calendar_attendance_filtered_one2many", calendarOne2Many);
