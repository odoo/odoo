/** @odoo-module */
import { Component } from "@odoo/owl";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { sortBy } from "@web/core/utils/arrays";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

import { Record } from "@web/model/record";
import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { CharField } from "@web/views/fields/char/char_field";
import { TextField } from "@web/views/fields/text/text_field";

import { viewTypeToString, useStudioServiceAsReactive } from "@web_studio/studio_service";
import { NewViewDialog } from "../editor/new_view_dialogs/new_view_dialog";
import { MapNewViewDialog } from "../editor/new_view_dialogs/map_new_view_dialog";

function getViewCategories() {
    return {
        general: {
            title: _t("General views"),
            viewTypes: ["form", "search", "activity"],
        },
        multiple: {
            title: _t("Multiple records views"),
            viewTypes: ["list", "kanban", "map"],
        },
        timeline: {
            title: _t("Timeline views"),
            viewTypes: ["calendar", "cohort", "gantt"],
        },
        reporting: {
            title: _t("Reporting views"),
            viewTypes: ["graph", "pivot"],
        },
    };
}

const actionFieldsGet = {
    id: { type: "integer" },
    name: { type: "char" },
    help: { type: "text" },
    groups_id: { type: "many2many", relation: "res.groups", string: "Groups" },
};

function getActionActiveFields() {
    const activeFields = {};
    for (const fName of Object.keys(actionFieldsGet)) {
        activeFields[fName] = {};
    }

    const groups_idRelated = Object.fromEntries(
        many2ManyTagsField.relatedFields({ options: {} }).map((f) => [f.name, f])
    );
    activeFields.groups_id.related = { activeFields: groups_idRelated, fields: groups_idRelated };

    return activeFields;
}

function getActionValues(action) {
    const values = {};
    for (const fName of Object.keys(actionFieldsGet)) {
        values[fName] = action[fName];
    }
    return values;
}

class ActionEditor extends Component {
    setup() {
        this.studio = useStudioServiceAsReactive();
        this.action = useService("action");
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        this.user = useService("user");
        this.viewCategories = getViewCategories();
        this.addDialog = useOwnedDialogs();

        this.actionFieldsGet = { ...actionFieldsGet };
    }

    get actionRecordProps() {
        const values = getActionValues(this.studio.editedAction);
        return {
            fields: this.actionFieldsGet,
            resModel: "ir.actions.act_window",
            resId: values.id,
            mode: "edit",
            values,
            activeFields: getActionActiveFields(),
            onRecordChanged: (record, changes) => {
                return this.editAction(changes);
            },
        };
    }

    get activeViews() {
        return this.studio.editedAction.views.map(([, name]) => name);
    }

    getOrderedViewTypes(viewTypes) {
        const activeViews = this.activeViews;
        const currentDefaultView = activeViews[0];
        const viewInfos = viewTypes.map((viewType) => {
            return {
                name: viewType,
                title: viewTypeToString(viewType),
                isActive: activeViews.includes(viewType),
                isDefault: currentDefaultView === viewType,
                imgUrl: `/web_studio/static/src/img/view_type/${viewType}.png`,
                canBeDefault: !["form", "search"].includes(viewType),
                canBeDisabled: viewType !== "search",
            };
        });
        return sortBy(
            viewInfos,
            ({ isDefault, isActive }) => {
                return isDefault ? 2 : isActive ? 1 : 0;
            },
            "desc"
        );
    }

    setDefaultView(viewType) {
        viewType = viewType === "tree" ? "list" : viewType;
        let viewModes = this.studio.editedAction.view_mode.split(",");
        viewModes = viewModes.filter((m) => m !== viewType);
        viewModes.unshift(viewType);
        return this.editAction({ view_mode: viewModes.join(",") });
    }

    disableView(viewType) {
        const viewMode = this.studio.editedAction.view_mode
            .split(",")
            .filter((m) => m !== viewType);

        if (!viewMode.length) {
            this.addDialog(AlertDialog, {
                body: _t("You cannot deactivate this view as it is the last one active."),
            });
        } else {
            return this.editAction({ view_mode: viewMode.join(",") });
        }
    }

    restoreDefaultView(viewType) {
        return this.env.editionFlow.restoreDefaultView(null, viewType);
    }

    async addViewType(viewType) {
        const action = this.studio.editedAction;
        const viewMode = action.view_mode.split(",");
        viewMode.push(viewType);
        let viewAdded = await this.rpc("/web_studio/add_view_type", {
            action_type: action.type,
            action_id: action.id,
            res_model: action.res_model,
            view_type: viewType,
            args: { view_mode: viewMode.join(",") },
            context: this.user.context,
        });

        if (viewAdded !== true) {
            viewAdded = await new Promise((resolve) => {
                let DialogClass;
                const dialogProps = {
                    confirm: async () => {
                        resolve(true);
                    },
                    cancel: () => resolve(false),
                };
                if (["gantt", "calendar", "cohort"].includes(viewType)) {
                    DialogClass = NewViewDialog;
                    dialogProps.viewType = viewType;
                } else if (viewType === "map") {
                    DialogClass = MapNewViewDialog;
                } else {
                    this.addDialog(AlertDialog, {
                        body: _t(
                            "Creating this type of view is not currently supported in Studio."
                        ),
                    });
                    resolve(false);
                }
                this.addDialog(DialogClass, dialogProps);
            });
        }
        if (viewAdded) {
            await this.editAction({ view_mode: viewMode.join(",") });
        }
        return viewAdded;
    }

    editView(viewType) {
        this.studio.setParams({ viewType, editorTab: "views" });
    }

    async onThumbnailClicked(viewType) {
        if (this.activeViews.includes(viewType)) {
            return this.editView(viewType);
        }
        const resModel = this.studio.editedAction.res_model;
        if (viewType === "activity") {
            const activityAllowed = await this.studio.isAllowed("activity", resModel);
            if (!activityAllowed) {
                this.notification.add(
                    _t("Activity view unavailable on this model"),
                    {
                        title: false,
                        type: "danger",
                    }
                );
                return;
            }
        }
        if (await this.addViewType(viewType)) {
            return this.editView(viewType);
        }
    }

    openFormAction() {
        return this.action.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "ir.actions.act_window",
                res_id: this.studio.editedAction.id,
                views: [[false, "form"]],
                target: "current",
            },
            {
                stackPosition: "replacePreviousAction",
            }
        );
    }

    async editAction(changes) {
        await this.rpc("/web_studio/edit_action", {
            action_id: this.studio.editedAction.id,
            action_type: "ir.actions.act_window",
            args: changes,
        });
        return this.studio.reload({}, false);
    }
}
ActionEditor.template = "web_studio.ActionEditor";
ActionEditor.components = {
    Dropdown,
    DropdownItem,
    Record,
    CharField,
    TextField,
    Many2ManyTagsField,
};
ActionEditor.props = { ...standardActionServiceProps };

registry.category("actions").add("web_studio.action_editor", ActionEditor);
