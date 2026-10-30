import { Plugin, signal, useConfig, usePlugin, t, proxy } from "@odoo/owl";
import { serializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { ORM } from "@web/core/orm_plugin";
import { user } from "@web/core/user";
import { download } from "@web/core/network/download";
import { omit } from "@web/core/utils/objects";

const { DateTime } = luxon;

export const reportExtensionRegistry = registry.category("pos_report_extensions");

reportExtensionRegistry.addValidation(
    t.object({
        handler: t.string(),
        slot: t.string(),
        component: t.function(),
    })
);

export const SLOT_LINE_NAME = "TreeNode.name";
export const SLOT_REPORT_HEADER = "PosReport.header";

export class PosReportPlugin extends Plugin {
    orm = usePlugin(ORM);
    ui = useConfig("ui", t.object());
    action = useConfig("action", t.object());

    reportId = this.action.context?.report_id;
    meta = signal(null);
    options = signal({});
    state = proxy({ sections: [] });
    sessionOptionsKey = `pos.report:${this.reportId}:${user.activeCompany.id}`;

    get sections() {
        return this.state.sections || [];
    }

    getExtensions(slot) {
        const handler = this.meta()?.handler;
        if (!handler) {
            return [];
        }
        return reportExtensionRegistry
            .getAll()
            .filter((extension) => extension.handler === handler && extension.slot === slot);
    }

    saveSessionOptions() {
        if (this.action.context.ignore_session) {
            return;
        }
        window.sessionStorage.setItem(this.sessionOptionsKey, JSON.stringify(this.options()));
    }

    async loadReportInfo() {
        const info = await this.orm.call("pos.report", "get_report_info", [[this.reportId]]);
        this.meta.set({
            id: info.id,
            name: info.name,
            handler: info.handler,
            filters: info.filters || [],
        });

        await this._initializeFilters();

        if (!this.action.context.ignore_session) {
            const savedOptions = JSON.parse(window.sessionStorage.getItem(this.sessionOptionsKey));
            const defaults = this.action.context.default_filters || {};
            this.options.set({
                ...this.options(),
                ...omit(savedOptions || {}, ...Object.keys(defaults)),
            });
        }
    }

    async _initializeFilters() {
        const defaults = this.action.context.default_filters || {};
        for (const filter of this.meta().filters || []) {
            if (filter.key in defaults) {
                this.options.set({ ...this.options(), [filter.key]: defaults[filter.key] });
            } else if (filter.type === "date_range") {
                this._initDateFilter(filter);
            } else if (filter.type === "multi_select") {
                this.options.set({ ...this.options(), [filter.key]: [] });
            } else if (filter.type === "single_select") {
                this.options.set({ ...this.options(), [filter.key]: false });
            }
        }
    }

    _initDateFilter(filter) {
        const now = DateTime.now();
        const rangeType = filter.default || "month";

        let date_from, date_to;
        switch (rangeType) {
            case "year":
                date_from = now.startOf("year");
                date_to = now.endOf("year");
                break;
            case "month":
            default:
                date_from = now.startOf("month");
                date_to = now.endOf("month");
                break;
        }
        this.options.set({
            ...this.options(),
            date_from: serializeDateTime(date_from),
            date_to: serializeDateTime(date_to),
        });
    }

    setReportData(data) {
        this.meta.set({
            ...this.meta(),
            name: data.report_name,
            currency: data.currency,
            extensionData: data.extension_data || {},
        });
    }

    async loadReport() {
        try {
            await this.loadReportInfo();
            const data = await this.orm.call("pos.report", "get_report_data", [[this.reportId]], {
                options: { ...this.options() },
            });

            this.setReportData(data);
            const sections = data.sections || [];
            if (this.options().unfold_all) {
                this._markExpanded(sections);
            }
            this.state.sections = sections;
        } catch (e) {
            console.error(e);
        }
    }

    getFilterDomain(filter) {
        const options = this.options();
        const domain = [];

        for (const [field, operator, value] of filter.domain || []) {
            const isOptionReference = typeof value === "string" && value in options;
            if (isOptionReference) {
                const optionValue = options[value];
                if (Array.isArray(optionValue) ? optionValue.length : optionValue) {
                    domain.push([
                        field,
                        operator,
                        ["in", "not in"].includes(operator) && !Array.isArray(optionValue)
                            ? [optionValue]
                            : optionValue,
                    ]);
                }
            } else {
                domain.push([field, operator, value]);
            }
        }

        return domain;
    }

    async applyFilters(newOptions = {}) {
        const previousOptions = this.options();
        const options = { ...previousOptions, ...newOptions };
        for (const filter of this.meta().filters) {
            if (!filter.domain) {
                continue;
            }

            const parentChanged = filter.domain.some(
                ([, , key]) =>
                    typeof key === "string" &&
                    key in newOptions &&
                    JSON.stringify(newOptions[key]) !== JSON.stringify(previousOptions[key])
            );

            if (parentChanged && !(filter.key in newOptions)) {
                options[filter.key] = filter.type === "multi_select" ? [] : false;
            }
        }
        this.options.set(options);
        this.saveSessionOptions();

        // Preserve expanded state per section using composite key
        const foldabilityByKey = {};
        for (const section of this.sections) {
            const key = section.section_id + "_" + (section.record_id ?? "");
            foldabilityByKey[key] = section.foldability;
        }

        try {
            const data = await this.orm.call("pos.report", "get_report_data", [[this.reportId]], {
                options: { ...this.options() },
            });

            this.setReportData(data);

            const newSections = data.sections || [];

            // Restore expanded state from previous sections.
            // Backend already includes children for default-expanded sections.
            for (const section of newSections) {
                const key = section.section_id + "_" + (section.record_id ?? "");
                if (foldabilityByKey[key] !== undefined) {
                    section.foldability = foldabilityByKey[key];
                }
                // Clear children for non-expanded sections
                if (section.foldability !== "expanded") {
                    section.lines = [];
                }
            }

            this.state.sections = newSections;
            await Promise.all(
                this.state.sections
                    .filter((s) => s.foldability === "expanded" && !s.lines?.length)
                    .map((s) => this.unfoldLine(s.section_id, s))
            );
        } catch (e) {
            console.error(e);
        }
    }

    async unfoldAll() {
        try {
            const shouldUnfold = !this.options().unfold_all;
            this.options.set({ ...this.options(), unfold_all: shouldUnfold });
            this.saveSessionOptions();

            const data = await this.orm.call("pos.report", "get_report_data", [[this.reportId]], {
                options: { ...this.options() },
            });

            this.setReportData(data);

            const newSections = data.sections || [];
            if (shouldUnfold) {
                this._markExpanded(newSections);
            }

            this.state.sections = newSections;
        } catch (e) {
            console.error(e);
        }
    }

    _markExpanded(lines) {
        for (const line of lines || []) {
            if (line.foldability === "static") {
                continue;
            }
            line.foldability = "expanded";
            if (line.lines?.length) {
                this._markExpanded(line.lines);
            }
        }
    }

    toggleUnfold(line) {
        if (line.foldability === "expanded") {
            this.foldLine(line);
        } else {
            return this.unfoldLine(line.section_id, line);
        }
    }

    async unfoldLine(sectionId, line) {
        try {
            const data = await this.orm.call("pos.report", "get_unfold_data", [[this.reportId]], {
                options: { ...this.options(), record_id: line.record_id ?? null },
                section_id: sectionId,
            });
            line.lines = data.lines || [];
            line.foldability = "expanded";
        } catch (e) {
            console.error(e);
        }
    }

    foldLine(line) {
        line.foldability = "collapsed";
        line.lines = [];

        if (this.options().unfold_all) {
            this.options.set({ ...this.options(), unfold_all: false });
            this.saveSessionOptions();
        }
    }

    async exportReport(format) {
        try {
            this.ui.block();
            const url = "/pos_reports";
            const data = {
                report_id: this.reportId,
                export_format: format,
                options: JSON.stringify({
                    ...this.options(),
                    allowed_company_ids: user.context.allowed_company_ids,
                }),
            };

            await download({ url, data });
        } finally {
            this.ui.unblock();
        }
    }
}

export function usePosReport() {
    return usePlugin(PosReportPlugin);
}
