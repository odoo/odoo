/** @odoo-module **/

import { Component, useState, onWillStart, onWillUpdateProps, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { standardViewProps } from "@web/views/standard_view_props";
import { useSetupAction } from "@web/search/action_hook";
import { GanttRenderer } from "./gantt_renderer";
import { GanttModel } from "./gantt_model";

export class GanttController extends Component {
    static template = "school_management.GanttController";
    static components = { Layout, SearchBar, CogMenu, GanttRenderer };
    static props = {
        ...standardViewProps,
        archInfo: Object,
        Model: { type: Function, optional: true },
        Renderer: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.model = useState(new GanttModel(this.orm, this.props.resModel, this.props.archInfo));
        this.searchBarToggler = useSearchBarToggler();

        useSetupAction({
            rootRef: useRef("root"),
        });

        onWillStart(async () => {
            const domain = this.props.domain || [];
            await this.model.load(domain);
        });

        onWillUpdateProps(async (nextProps) => {
            if (JSON.stringify(this.props.domain) !== JSON.stringify(nextProps.domain)) {
                await this.model.load(nextProps.domain || []);
            }
        });
    }

    get display() {
        const { controlPanel } = this.props.display || {};
        if (!controlPanel) {
            return {
                ...this.props.display,
                controlPanel: {
                    layoutActions: true,
                },
            };
        }
        return {
            ...this.props.display,
            controlPanel: {
                ...controlPanel,
                layoutActions: true,
            },
        };
    }

    openTimetableWizard() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Generate Timetable",
            res_model: "university.timetable.generation.wizard",
            views: [[false, "form"]],
            view_mode: "form",
            target: "new",
        }, {
            onClose: async () => {
                await this.model.load(this.props.domain || []);
            },
        });
    }

    async onClickNew() {
        const bounds = this.model.getWeekBounds(this.model.currentDate);
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "New Shift",
            res_model: this.props.resModel,
            views: [[false, "form"]],
            view_mode: "form",
            target: "new",
            context: {
                default_start_time: `${bounds.start} 08:00:00`,
                default_end_time: `${bounds.start} 10:00:00`,
                default_generation_state: "draft",
                default_state: "draft",
            },
        }, {
            onClose: async () => {
                await this.model.load(this.props.domain || []);
            },
        });
    }

    async onClickPublish() {
        try {
            const res = await this.model.publishWeek();
            const count = res?.published_count || 0;
            this.notification.add(`${count} session(s) published for this week.`, {
                type: "success",
            });
        } catch (err) {
            this.notification.add(err.message || "Could not publish week sessions.", {
                type: "danger",
            });
        }
    }

    async onClickCopyPreviousWeek() {
        if (!confirm("Copy all scheduled shifts from the previous week into the current week as draft?")) {
            return;
        }
        try {
            const res = await this.model.copyPreviousWeek();
            const count = res?.copied_count || 0;
            this.notification.add(`Copied ${count} shift(s) from previous week.`, {
                type: "success",
            });
        } catch (err) {
            this.notification.add(err.message || "Failed to copy previous week.", {
                type: "danger",
            });
        }
    }

    openSlot(slotId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Shift Details",
            res_model: this.props.resModel,
            res_id: slotId,
            views: [[false, "form"]],
            view_mode: "form",
            target: "new",
        }, {
            onClose: async () => {
                await this.model.load(this.props.domain || []);
            },
        });
    }

    createSlot(resourceId, dateStr) {
        const ctx = {
            default_start_time: `${dateStr} 08:00:00`,
            default_end_time: `${dateStr} 12:00:00`,
            default_generation_state: "draft",
            default_state: "draft",
        };
        if (resourceId) {
            ctx.default_resource_id = resourceId;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "New Shift",
            res_model: this.props.resModel,
            views: [[false, "form"]],
            view_mode: "form",
            target: "new",
            context: ctx,
        }, {
            onClose: async () => {
                await this.model.load(this.props.domain || []);
            },
        });
    }

    exportSchedule() {
        const slots = this.model.slots || [];
        if (!slots.length) {
            this.notification.add("No schedule records to export.", { type: "warning" });
            return;
        }
        const headers = ["Date", "Start Time", "End Time", "Resource", "Title", "Room", "Status", "Hours"];
        const rows = slots.map((s) => [
            s.start_date || "",
            s.start_time_str || "",
            s.end_time_str || "",
            `"${(s.resource_name || "Open Shift").replace(/"/g, '""')}"`,
            `"${(s.name || "").replace(/"/g, '""')}"`,
            `"${(s.room_name || "").replace(/"/g, '""')}"`,
            s.state || "draft",
            s.allocated_hours || 0,
        ]);
        const csvContent = "\uFEFF" + [headers.join(","), ...rows.map((r) => r.join(","))].join("\r\n");
        const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", `Schedule_by_Resource_${this.model.rangeLabel.replace(/[\s·-]+/g, "_")}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        this.notification.add("Schedule exported to CSV successfully.", { type: "success" });
    }

    switchToList() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Schedule by Resource",
            res_model: this.props.resModel,
            views: [[false, "list"], [false, "form"]],
            view_mode: "list,form",
            target: "current",
        });
    }
}
