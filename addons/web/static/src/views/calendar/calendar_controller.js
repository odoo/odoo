import {
    deleteConfirmationMessage,
    ConfirmationDialog,
} from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useBus, useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { useModelWithSampleData } from "@web/model/model";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { CallbackRecorder, useSetupAction } from "@web/search/action_hook";
import { CalendarMobileFilterPanel } from "./mobile_filter_panel/calendar_mobile_filter_panel";
import { CalendarQuickCreate } from "./quick_create/calendar_quick_create";
import { CalendarSidePanel } from "@web/views/calendar/calendar_side_panel/calendar_side_panel";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { ViewScaleSelector } from "@web/views/view_components/view_scale_selector";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { browser } from "@web/core/browser/browser";
import { standardViewProps } from "@web/views/standard_view_props";
import {
    MultiSelectionButtons,
    useMultiSelectionButtons,
} from "@web/views/view_components/multi_selection_buttons";
import { getLocalYearAndWeek } from "@web/core/l10n/dates";

import { Component, useState } from "@odoo/owl";

const { DateTime } = luxon;

export const SCALE_LABELS = {
    day: _t("Day"),
    week: _t("Week"),
    month: _t("Month"),
    year: _t("Year"),
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
    static components = {
        MobileFilterPanel: CalendarMobileFilterPanel,
        QuickCreate: CalendarQuickCreate,
        QuickCreateFormView: FormViewDialog,
        Layout,
        SearchBar,
        ViewScaleSelector,
        CogMenu,
        CalendarSidePanel,
        MultiSelectionButtons,
    };
    static template = "web.CalendarController";
    static props = {
        ...standardViewProps,
        Model: Function,
        Renderer: Function,
        archInfo: Object,
        buttonTemplate: String,
        itemCalendarProps: { type: Object, optional: true },
    };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.displayDialog = useUniqueDialog();

        this.model = useModelWithSampleData(this.props.Model, this.modelParams);

        useSetupAction({
            getLocalState: () => this.model.exportedState,
        });

        const sessionShowSidebar = browser.sessionStorage.getItem("calendar.showSideBar");
        this.state = useState({
            isWeekendVisible:
                browser.localStorage.getItem("calendar.isWeekendVisible") != null
                    ? JSON.parse(browser.localStorage.getItem("calendar.isWeekendVisible"))
                    : true,
            showSideBar:
                !this.env.isSmall &&
                Boolean(sessionShowSidebar != null ? JSON.parse(sessionShowSidebar) : true),
        });

        this.searchBarToggler = useSearchBarToggler();

        this._baseRendererProps = {
            createRecord: this.createRecord.bind(this),
            deleteRecord: this.deleteRecord.bind(this),
            editRecord: this.editRecord.bind(this),
            setDate: this.setDate.bind(this),
        };

        this.prepareSelectionFeature();
    }

    get modelParams() {
        return {
            ...this.props.archInfo,
            resModel: this.props.resModel,
            domain: this.props.domain,
            fields: this.props.fields,
            date: this.props.state?.date,
        };
    }

    get currentDate() {
        const meta = this.model.meta;
        const scale = meta.scale;
        if (this.env.isSmall && ["week", "month"].includes(scale)) {
            const date = meta.date || DateTime.now();
            let text = "";
            if (scale === "week") {
                const startMonth = date.startOf("week");
                const endMonth = date.endOf("week");
                if (startMonth.toFormat("LLL") !== endMonth.toFormat("LLL")) {
                    text = `${startMonth.toFormat("LLL")}-${endMonth.toFormat("LLL")}`;
                } else {
                    text = startMonth.toFormat("LLLL");
                }
            } else if (scale === "month") {
                text = date.toFormat("LLLL");
            }
            return ` - ${text} ${date.year}`;
        } else {
            return "";
        }
    }

    get date() {
        return this.model.meta.date || DateTime.now();
    }

    get today() {
        return DateTime.now().toFormat("d");
    }

    get currentYear() {
        return this.date.toFormat("y");
    }

    get dayHeader() {
        return `${this.date.toFormat("d")} ${this.date.toFormat("MMMM")} ${this.date.year}`;
    }

    get weekHeader() {
        const { rangeStart, rangeEnd } = this.model;
        if (rangeStart.year != rangeEnd.year) {
            return `${rangeStart.toFormat("MMMM")} ${rangeStart.year} - ${rangeEnd.toFormat(
                "MMMM"
            )} ${rangeEnd.year}`;
        } else if (rangeStart.month != rangeEnd.month) {
            return `${rangeStart.toFormat("MMMM")} - ${rangeEnd.toFormat("MMMM")} ${
                rangeStart.year
            }`;
        }
        return `${rangeStart.toFormat("MMMM")} ${rangeStart.year}`;
    }

    get currentMonth() {
        return `${this.date.toFormat("MMMM")} ${this.date.year}`;
    }

    get currentWeek() {
        return getLocalYearAndWeek(this.model.rangeStart).week;
    }

    get rendererProps() {
        return {
            ...this._baseRendererProps,
            model: this.model,
            isWeekendVisible: this.model.scale === "day" || this.state.isWeekendVisible,
        };
    }

    get mobileFilterPanelProps() {
        return {
            model: this.model,
            sideBarShown: this.state.showSideBar,
            toggleSideBar: () => {
                this.state.showSideBar = !this.state.showSideBar;
            },
        };
    }

    get sidePanelProps() {
        return { model: this.model };
    }

    toggleSideBar() {
        this.state.showSideBar = !this.state.showSideBar;
        browser.sessionStorage.setItem("calendar.showSideBar", this.state.showSideBar);
    }

    get showCalendar() {
        return !this.env.isSmall || !this.state.showSideBar;
    }

    get hasSideBar() {
        return this.model.showDatePicker || this.model.filterSections.length > 0;
    }

    get showSideBar() {
        return this.state.showSideBar;
    }

    get className() {
        return this.props.className;
    }

    get editRecordDefaultDisplayText() {
        return _t("New Event");
    }

    prepareSelectionFeature() {
        this.selectedCells = null;
        this.multiSelectionButtonsReactive = useMultiSelectionButtons({
            onCancel: this.cleanSquareSelection.bind(this),
            onAdd: (multiCreateData) => {
                this.onMultiCreate(multiCreateData, this.selectedCells);
                this.cleanSquareSelection();
            },
            onDelete: () => {
                this.onMultiDelete(this.selectedCells);
                this.cleanSquareSelection();
            },
            nbSelected: 0,
            multiCreateView: this.model.meta.multiCreateView,
            resModel: this.model.meta.resModel,
            multiCreateValues: this.props.state?.multiCreateValues,
            showMultiCreateTimeRange: this.model.showMultiCreateTimeRange,
            context: this.props.context,
        });

        this.callbackRecorder = new CallbackRecorder();
        this._baseRendererProps.callbackRecorder = this.callbackRecorder;
        this._baseRendererProps.onSquareSelection = (selectedCells) => {
            if (selectedCells.length) {
                this.selectedCells = selectedCells;
                this.multiSelectionButtonsReactive.visible = true;
                this.multiSelectionButtonsReactive.nbSelected = this.getSelectedRecordIds(
                    this.selectedCells
                ).length;
            } else {
                this.selectedCells = null;
                this.multiSelectionButtonsReactive.visible = false;
                this.multiSelectionButtonsReactive.nbSelected = 0;
            }
        };
        this._baseRendererProps.cleanSquareSelection = this.cleanSquareSelection.bind(this);

        useBus(this.model.bus, "update", this.cleanSquareSelection.bind(this));
    }

    cleanSquareSelection() {
        this.selectedCells = null;
        this.multiSelectionButtonsReactive.visible = false;
        this.callbackRecorder.callbacks.forEach((fn) => fn());
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
            title: _t("New Event"),
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
    async editRecord(record, context = {}) {
        if (this.model.hasEditDialog) {
            return new Promise((resolve) => {
                this.displayDialog(
                    FormViewDialog,
                    {
                        resModel: this.model.resModel,
                        resId: record.id || false,
                        context,
                        title: record.id
                            ? _t("Open: %s", record.title)
                            : this.editRecordDefaultDisplayText,
                        viewId: this.model.formViewId,
                        onRecordSaved: () => this.model.load(),
                    },
                    { onClose: () => resolve() }
                );
            });
        } else {
            const action = {
                type: "ir.actions.act_window",
                res_model: this.model.resModel,
                views: [[this.model.formViewId || false, "form"]],
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
        return this.editRecord(record, context);
    }

    deleteConfirmationDialogProps(record) {
        return {
            title: _t("Bye-bye, record!"),
            body: deleteConfirmationMessage,
            confirm: () => {
                this.model.unlinkRecord(record.id);
            },
            confirmLabel: _t("Delete"),
            cancel: () => {
                // `ConfirmationDialog` needs this prop to display the cancel
                // button but we do nothing on cancel.
            },
            cancelLabel: _t("No, keep it"),
        };
    }

    deleteRecord(record) {
        this.displayDialog(ConfirmationDialog, this.deleteConfirmationDialogProps(record));
    }

    getDates(selectedCells) {
        const dates = [];
        for (const element of selectedCells) {
            const date = luxon.DateTime.fromISO(element.dataset.date);
            if (!date.invalid) {
                dates.push(date);
            }
        }
        return dates;
    }

    onMultiCreate(multiCreateData, selectedCells) {
        const dates = this.getDates(selectedCells);
        return this.model.multiCreateRecords(multiCreateData, dates);
    }

    getSelectedRecordIds(selectedCells) {
        const ids = [];
        for (const element of selectedCells) {
            for (const event of [...element.querySelectorAll(".fc-event")]) {
                ids.push(parseInt(event.dataset.eventId, 10));
            }
        }
        return ids;
    }

    onMultiDelete(selectedCells) {
        const ids = this.getSelectedRecordIds(selectedCells);
        return this.model.unlinkRecords(ids);
    }

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
                if (date.ts === this.date.startOf("day").ts) {
                    this.model.bus.trigger("SCROLL_TO_CURRENT_HOUR", false);
                }
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

    toggleWeekendVisibility() {
        this.state.isWeekendVisible = !this.state.isWeekendVisible;
        browser.localStorage.setItem("calendar.isWeekendVisible", this.state.isWeekendVisible);
    }
}
