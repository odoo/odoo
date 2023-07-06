/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t, _lt } from "@web/core/l10n/translation";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { Layout } from "@web/search/layout";
import { useModel } from "@web/views/model";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { useSetupView } from "@web/views/view_hook";
import { CalendarDatePicker } from "./date_picker/calendar_date_picker";
import { CalendarFilterPanel } from "./filter_panel/calendar_filter_panel";
import { CalendarMobileFilterPanel } from "./mobile_filter_panel/calendar_mobile_filter_panel";
import { CalendarQuickCreate } from "./quick_create/calendar_quick_create";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { ViewScaleSelector } from "@web/views/view_components/view_scale_selector";
import { CogMenu } from "@web/search/cog_menu/cog_menu";

import { Component, useState } from "@odoo/owl";

export const SCALE_LABELS = {
    day: _lt("Day"),
    week: _lt("Week"),
    month: _lt("Month"),
    year: _lt("Year"),
};

function useUniqueDialog() {
    const displayDialog = useOwnedDialogs();
    let close = null;
    return (...args) => {
        if (close) {
            close();
        }
        close = displayDialog(...args);
    };
}

export class CalendarController extends Component {
    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.displayDialog = useUniqueDialog();

        this.model = useModel(this.props.Model, {
            ...this.props.archInfo,
            resModel: this.props.resModel,
            domain: this.props.domain,
            fields: this.props.fields,
        }, {
            onWillStart: this.onWillStartModel.bind(this),
        });

        useSetupView({
            getLocalState: () => this.model.exportedState,
        });

        this.state = useState({
            showSideBar: !this.env.isSmall,
        });

        this.searchBarToggler = useSearchBarToggler();
    }

    get rendererProps() {
        return {
            model: this.model,
            createRecord: this.createRecord.bind(this),
            deleteRecord: this.deleteRecord.bind(this),
            editRecord: this.editRecord.bind(this),
            setDate: this.setDate.bind(this),
        };
    }
    get containerProps() {
        return {
            model: this.model,
        };
    }
    get datePickerProps() {
        return {
            model: this.model,
        };
    }
    get filterPanelProps() {
        return {
            model: this.model,
        };
    }
    get mobileFilterPanelProps() {
        return {
            model: this.model,
            sideBarShown: this.state.showSideBar,
            toggleSideBar: () => (this.state.showSideBar = !this.state.showSideBar),
        };
    }

    get showCalendar() {
        return !this.env.isSmall || !this.state.showSideBar;
    }

    get showSideBar() {
        return this.state.showSideBar;
    }

    get className() {
        return this.props.className;
    }

    getQuickCreateProps(record) {
        return {
            record,
            model: this.model,
            editRecord: this.editRecordInCreation.bind(this),
            title: this.props.context.default_name,
        };
    }

    getQuickCreateFormViewProps(record) {
        const rawRecord = this.model.buildRawRecord(record);
        const context = this.model.makeContextDefaults(rawRecord);
        return {
            resModel: this.model.resModel,
            viewId: this.model.quickCreateFormViewId,
            context,
        };
    }

    createRecord(record) {
        if (!this.model.canCreate) {
            return;
        }
        if (this.model.hasQuickCreate) {
            if (this.model.quickCreateFormViewId) {
                return new Promise((resolve) => {
                    this.displayDialog(
                        this.constructor.components.QuickCreateFormView,
                        this.getQuickCreateFormViewProps(record),
                        {
                            onClose: () => resolve(),
                        }
                    );
                });
            }

            return new Promise((resolve) => {
                this.displayDialog(
                    this.constructor.components.QuickCreate,
                    this.getQuickCreateProps(record),
                    {
                        onClose: () => resolve(),
                    }
                );
            });
        } else {
            return this.editRecordInCreation(record);
        }
    }
    async editRecord(record, context = {}, shouldFetchFormViewId = true) {
        if (this.model.hasEditDialog) {
            return new Promise((resolve) => {
                this.displayDialog(
                    FormViewDialog,
                    {
                        resModel: this.model.resModel,
                        resId: record.id || false,
                        context,
                        title: record.id ? sprintf(_t("Open: %s"), record.title) : _t("New Event"),
                        viewId: this.model.formViewId,
                        onRecordSaved: () => this.model.load(),
                    },
                    { onClose: () => resolve() }
                );
            });
        } else {
            let formViewId = this.model.formViewId;
            if (shouldFetchFormViewId) {
                formViewId = await this.orm.call(
                    this.model.resModel,
                    "get_formview_id",
                    [[record.id]],
                    context
                );
            }
            const action = {
                type: "ir.actions.act_window",
                res_model: this.model.resModel,
                views: [[formViewId || false, "form"]],
                target: "current",
                context,
            };
            if (record.id) {
                action.res_id = record.id;
            }
            this.action.doAction(action);
        }
    }
    editRecordInCreation(record) {
        const rawRecord = this.model.buildRawRecord(record);
        const context = this.model.makeContextDefaults(rawRecord);
        return this.editRecord(record, context, false);
    }
    deleteRecord(record) {
        this.displayDialog(ConfirmationDialog, {
            title: this.env._t("Confirmation"),
            body: this.env._t("Are you sure you want to delete this record?"),
            confirm: () => {
                this.model.unlinkRecord(record.id);
            },
            confirmLabel: _lt("Delete"),
            cancel: () => {
                // `ConfirmationDialog` needs this prop to display the cancel
                // button but we do nothing on cancel.
            },
        });
    }

    onWillStartModel() {}
    
    async setDate(move) {
        let date = null;
        switch (move) {
            case "next":
                date = this.model.date.plus({ [`${this.model.scale}s`]: 1 });
                break;
            case "previous":
                date = this.model.date.minus({ [`${this.model.scale}s`]: 1 });
                break;
            case "today":
                date = luxon.DateTime.local().startOf("day");
                break;
        }
        await this.model.load({ date });
    }

    get scales() {
        return Object.fromEntries(
            this.model.scales.map((s) => [s, { description: SCALE_LABELS[s] }])
        );
    }

    async setScale(scale) {
        await this.model.load({ scale });
    }
}
CalendarController.components = {
    DatePicker: CalendarDatePicker,
    FilterPanel: CalendarFilterPanel,
    MobileFilterPanel: CalendarMobileFilterPanel,
    QuickCreate: CalendarQuickCreate,
    QuickCreateFormView: FormViewDialog,
    Layout,
    SearchBar,
    ViewScaleSelector,
    CogMenu,
};
CalendarController.template = "web.CalendarController";
