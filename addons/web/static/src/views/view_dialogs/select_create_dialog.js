import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { renderToMarkup } from "@web/core/utils/render";
import { View } from "@web/views/view";

import { FormViewDialog } from "./form_view_dialog";

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

let _defaultNoContentHelp;
function getDefaultNoContentHelp() {
    if (!_defaultNoContentHelp) {
        _defaultNoContentHelp = renderToMarkup("web.SelectCreateDialog.DefaultNoContentHelp");
    }
    return _defaultNoContentHelp;
}

export class SelectCreateDialog extends Component {
    static components = { Dialog, View };
    static template = "web.SelectCreateDialog";
    static props = {
        context: { type: Object, optional: true },
        domain: { type: Array, optional: true },
        dynamicFilters: { type: Array, optional: true },
        resModel: String,
        searchViewId: { type: [Number, { value: false }], optional: true },
        multiSelect: { type: Boolean, optional: true },
        onSelected: { type: Function, optional: true },
        close: { type: Function, optional: true },
        onCreateEdit: { type: Function, optional: true },
        title: { type: String, optional: true },
        noCreate: { type: Boolean, optional: true },
        onUnselect: { type: Function, optional: true },
        noContentHelp: { type: String, optional: true }, // Markup
    };
    static defaultProps = {
        dynamicFilters: [],
        multiSelect: true,
        searchViewId: false,
        domain: [],
        context: {},
    };

    setup() {
        this.viewService = useService("view");
        this.dialogService = useService("dialog");
        this.state = useState({ resIds: [] });
        const noContentHelp = this.props.noContentHelp || getDefaultNoContentHelp();
        this.busy = false; // flag used to ensure we only call once the onSelected/onUnselect props
        this.baseViewProps = {
            display: { searchPanel: false },
            editable: false, // readonly
            noBreadcrumbs: true,
            noContentHelp,
            showButtons: false,
            selectRecord: (resId) => this.select([resId]),
            onSelectionChanged: (resIds) => {
                this.state.resIds = resIds;
            },
        };
    }

    get viewProps() {
        const type = this.env.isSmall ? "kanban" : "list";
        const props = {
            loadIrFilters: true,
            ...this.baseViewProps,
            context: this.props.context,
            domain: this.props.domain,
            dynamicFilters: this.props.dynamicFilters,
            resModel: this.props.resModel,
            searchViewId: this.props.searchViewId,
            type,
        };
        if (type === "list") {
            props.allowSelectors = this.props.multiSelect;
            props.allowOpenAction = false;
        } else if (type === "kanban") {
            props.forceGlobalClick = true;
        }
        return props;
    }

    async executeOnceAndClose(callback) {
        if (!this.busy) {
            this.busy = true;
            try {
                await callback();
            } catch (e) {
                this.busy = false;
                throw e;
            }
            this.props.close();
        }
    }

    async select(resIds) {
        if (this.props.onSelected) {
            this.executeOnceAndClose(() => this.props.onSelected(resIds));
        }
    }

    async unselect() {
        if (this.props.onUnselect) {
            this.executeOnceAndClose(() => this.props.onUnselect());
        }
    }

    get canUnselect() {
        return this.env.isSmall && !!this.props.onUnselect;
    }

    async createEditRecord() {
        if (this.props.onCreateEdit) {
            await this.props.onCreateEdit();
            this.props.close();
        } else {
            this.dialogService.add(FormViewDialog, {
                context: this.props.context,
                resModel: this.props.resModel,
                onRecordSaved: (record) => {
                    this.props.onSelected([record.resId]);
                    this.props.close();
                },
            });
        }
    }
}

registry.category("dialogs").add("select_create", SelectCreateDialog);
