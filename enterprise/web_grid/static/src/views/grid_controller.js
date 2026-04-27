/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { serializeDate, deserializeDate } from "@web/core/l10n/dates";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { useModelWithSampleData } from "@web/model/model";
import { standardViewProps } from "@web/views/standard_view_props";
import { useViewButtons } from "@web/views/view_button/view_button_hook";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { ViewButton } from "@web/views/view_button/view_button";
import { useSetupAction } from "@web/search/action_hook";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { browser } from "@web/core/browser/browser";

import { Component, useState, onWillUnmount, useRef } from "@odoo/owl";

export class GridController extends Component {
    static components = {
        Layout,
        Dropdown,
        DropdownItem,
        ViewButton,
        CogMenu,
        SearchBar,
    };

    static props = {
        ...standardViewProps,
        archInfo: Object,
        buttonTemplate: String,
        Model: Function,
        Renderer: Function,
    };

    static template = "web_grid.GridView";

    setup() {
        const state = this.props.state || {};
        let activeRangeName = this.props.archInfo.activeRangeName;
        let defaultAnchor;
        if (state.activeRangeName) {
            activeRangeName = state.activeRangeName;
        } else if (this.isMobile && "day" in this.props.archInfo.ranges) {
            activeRangeName = "day";
        }
        if (state.anchor) {
            defaultAnchor = state.anchor;
        } else if (this.props.context.grid_anchor) {
            defaultAnchor = deserializeDate(this.props.context.grid_anchor);
        }
        this.dialogService = useService("dialog");
        this.model = useModelWithSampleData(this.props.Model, {
            resModel: this.props.resModel,
            sectionField: this.props.archInfo.sectionField,
            rowFields: this.props.archInfo.rowFields,
            columnFieldName: this.props.archInfo.columnFieldName,
            measureField: this.props.archInfo.measureField,
            readonlyField: this.props.archInfo.readonlyField,
            fieldsInfo: this.props.relatedModels[this.props.resModel].fields,
            activeRangeName,
            ranges: this.props.archInfo.ranges,
            defaultAnchor,
        });
        const rootRef = useRef("root");
        useSetupAction({
            rootRef: rootRef,
            getLocalState: () => {
                const { anchor, range } = this.model.navigationInfo;
                return {
                    anchor,
                    activeRangeName: range?.name,
                };
            }
        })
        const isWeekendVisible = browser.localStorage.getItem("grid.isWeekendVisible");
        this.state = useState({
            activeRangeName: this.model.navigationInfo.range?.name,
            isWeekendVisible: isWeekendVisible !== null && isWeekendVisible !== undefined
                ? JSON.parse(isWeekendVisible)
                : true,
        });
        useViewButtons(rootRef, {
            beforeExecuteAction: this.beforeExecuteActionButton.bind(this),
            afterExecuteAction: this.afterExecuteActionButton.bind(this),
            reload: this.reload.bind(this),
        });
        onWillUnmount(() => this.closeDialog?.());
        this.searchBarToggler = useSearchBarToggler();
    }

    get isMobile() {
        return this.env.isSmall;
    }

    get isEditable() {
        return (
            this.props.archInfo.activeActions.edit &&
            this.props.archInfo.editable
        );
    }

    get displayNoContent() {
        return (
            !(this.props.archInfo.displayEmpty || this.model.hasData()) || this.model.useSampleModel
        );
    }

    get displayAddALine() {
        return this.props.archInfo.activeActions.create;
    }

    get hasDisplayableData() {
        return true;
    }

    get options() {
        const { hideLineTotal, hideColumnTotal, hasBarChartTotal, createInline } =
            this.props.archInfo;
        return {
            hideLineTotal,
            hideColumnTotal,
            hasBarChartTotal,
            createInline,
        };
    }

    createRecord(params) {
        const columnContext = this.model.columnFieldIsDate
            ? {
                  [`default_${this.model.columnFieldName}`]: serializeDate(
                      this.model.navigationInfo.anchor
                  ),
              }
            : {};
        const context = {
            ...this.props.context,
            ...columnContext,
            ...(params?.context || {}),
        };
        this.closeDialog = this.dialogService.add(
            FormViewDialog,
            {
                title: _t("New Record"),
                resModel: this.model.resModel,
                viewId: this.props.archInfo.formViewId,
                onRecordSaved: this.onRecordSaved.bind(this),
                ...(params || {}),
                context,
            },
            {
                onClose: () => {
                    this.closeDialog = null;
                },
            }
        );
    }

    async beforeExecuteActionButton() {}

    async afterExecuteActionButton() {}

    async reload() {
        await this.model.fetchData();
    }

    async onRecordSaved(record) {
        await this.reload();
    }

    get columns() {
        return this.state.isWeekendVisible || ["day", "year"].includes(this.state.activeRangeName)
            ? this.model.columnsArray
            : this.model.columnsArray.filter((column) => {
                  return column.isWeekDay;
             });
    }

    toggleWeekendVisibility() {
        this.state.isWeekendVisible = !this.state.isWeekendVisible;
        browser.localStorage.setItem("grid.isWeekendVisible", this.state.isWeekendVisible);
    }
}
