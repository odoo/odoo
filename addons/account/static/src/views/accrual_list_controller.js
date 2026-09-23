/** @odoo-module native */
import { useEnv, useRef, useState } from "@odoo/owl";
import { useDateTimePicker } from "@web/components/datetime";
import { serializeDate } from "@web/core/l10n/dates";
import { ListController } from "@web/views/list";

import { DateTime } from "luxon";
export class AccrualListController extends ListController {
    setup() {
        super.setup();
        this.accrualContext = useEnv().accrualContext;
        this.state = useState({
            date: DateTime.now(),
        });
        this.dateAsString = serializeDate(this.state.date);
        if (this.model.config.resModel === "purchase.order.line") {
            this.model.config.fields.qty_transferred_at_date.aggregator = "sum";
        } else {
            this.model.config.fields.qty_transferred_at_date.aggregator = "sum";
        }
        this.model.config.fields.qty_invoiced_at_date.aggregator = "sum";
        this.model.config.fields.amount_to_invoice_at_date.aggregator = "sum";
        this.dateFilterRef = useRef("filterDate");
        const getPickerProps = () => {
            const pickerProps = {
                value: this.state.date,
                type: "date",
            };
            return pickerProps;
        };
        this.dateTimePicker = useDateTimePicker({
            target: "filterDate",
            get pickerProps() {
                return getPickerProps();
            },
            onApply: (newDate) => {
                if (newDate) {
                    this.setDate(newDate);
                }
            },
        });
    }

    async openRecord(record) {
        // Instead of opening the record itself, open the parent order.
        const res_model = record.model.config.fields.order_id.relation;
        this.actionService.doAction({
            name: record.data.order_id.display_name,
            type: "ir.actions.act_window",
            res_model,
            res_id: record.data.order_id.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async setDate(date) {
        this.dateAsString = serializeDate(date);
        this.model.config.context.accrual_entry_date = this.dateAsString;
        this.accrualContext.accrual_entry_date = this.dateAsString;
        this.state.date = date;

        if (this.model.config.groups) {
            // If records are grouped, update context of grouped lines too.
            for (const group of Object.values(this.model.config.groups)) {
                group.context.accrual_entry_date = this.dateAsString;
            }
        }

        await this.model.root.load();
        this.model.notify();
    }

    get date() {
        return this.state.date.toLocaleString();
    }

    onDateClick() {
        this.dateTimePicker.open();
    }

    async beforeExecuteActionButton(clickParams) {
        if (this.dateAsString) {
            // If a date was selected, use it as the default date for the wizard.
            clickParams.buttonContext.default_date = this.dateAsString;
        }
        return super.beforeExecuteActionButton(...arguments);
    }
}
