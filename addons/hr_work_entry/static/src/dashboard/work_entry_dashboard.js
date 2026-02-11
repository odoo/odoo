import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { serializeDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { formatFloatTime } from "@web/views/fields/formatters";

const { DateTime } = luxon;

export class WorkEntryDashboard extends Component {
    static template = "hr_work_entry.WorkEntryDashboard";
    static props = {
        employeeId: { type: Number, optional: true },
        rangeStart: { type: Object, optional: true },
        rangeEnd: { type: Object, optional: true },
        reloadKey: { type: Number, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ counters: [] });

        onWillStart(() => this.loadCounters());

        onWillUpdateProps(async (nextProps) => {
            const changed = this.props.employeeId !== nextProps.employeeId ||
                this.props.rangeStart?.toISODate?.() !== nextProps.rangeStart?.toISODate?.() ||
                this.props.rangeEnd?.toISODate?.() !== nextProps.rangeEnd?.toISODate?.() ||
                this.props.reloadKey !== nextProps.reloadKey;

            if (changed) {
                await this.loadCounters(nextProps);
            }
        });
    }

    get hasCounters() {
        return Boolean(this.state.counters.length);
    }

    async loadCounters(props = this.props) {
        const { employeeId, rangeStart } = props;
        if (!employeeId || !rangeStart) {
            this.state.counters = [];
            return;
        }

        const dt = DateTime.fromJSDate(rangeStart.toJSDate());

        const fetchSum = (start, end) => this.orm.formattedReadGroup(
            "hr.work.entry",
            [
                ["employee_id", "=", employeeId],
                ["date", ">=", serializeDate(start)],
                ["date", "<=", serializeDate(end)],
            ],
            ["work_entry_type_id"],
            ["duration:sum"]
        );

        const [monthGroups, yearGroups] = await Promise.all([
            fetchSum(dt.startOf("month"), dt.endOf("month")),
            fetchSum(dt.startOf("year"), dt.endOf("year")),
        ]);

        const typeIds = [...new Set([...monthGroups, ...yearGroups].map(g => g.work_entry_type_id?.[0]).filter(Boolean))];
        if (!typeIds.length) {
            this.state.counters = [];
            return;
        }

        const types = await this.orm.read(
            "hr.work.entry.type",
            typeIds,
            ["display_name", "counter_periodicity", "counter_use_cap", "counter_maximum_cap"]
        );

        const mUsed = Object.fromEntries(monthGroups.map(g => [g.work_entry_type_id[0], g["duration:sum"] || 0]));
        const yUsed = Object.fromEntries(yearGroups.map(g => [g.work_entry_type_id[0], g["duration:sum"] || 0]));

        this.state.counters = types.flatMap(type => {
            if (type.counter_periodicity === "none") {
                return [];
            }
            const isYearly = type.counter_periodicity === "year";
            const used = (isYearly ? yUsed : mUsed)[type.id] || 0;
            const cap = type.counter_maximum_cap || 0;
            const hasCap = Boolean(type.counter_use_cap && cap);

            if (used <= 0) return [];

            return {
                id: type.id,
                name: type.display_name,
                periodicity: type.counter_periodicity,
                periodLabel: isYearly ? _t("This Year") : _t("This Month"),
                used,
                cap,
                hasCap,
                usedStr: this._formatDuration(used),
                capStr: this._formatDuration(cap),
            };
        });
    }

    _formatDuration(duration) {
        return formatFloatTime(duration, { noLeadingZeroHour: true });
    }
}