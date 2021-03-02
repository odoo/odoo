/** @odoo-module **/

import { editModelDebug } from "../debug_manager/debug_manager_service";
import { Dialog } from "../components/dialog/dialog";
import { json_node_to_xml } from "../utils/misc";
import { formatMany2one } from "../utils/fields";

const { Component, hooks, tags } = owl;
const { useState } = hooks;

export function setupDebugAction(accessRights, env, action) {
  const actionSeparator = {
    type: "separator",
    sequence: 100,
  };

  let description = env._t("Edit Action");
  const editAction = {
    type: "item",
    description: description,
    callback: () => {
      editModelDebug(env, description, action.type, action.id);
    },
    sequence: 110,
  };

  description = env._t("View Fields");
  const viewFields = {
    type: "item",
    description: description,
    callback: async () => {
      const modelId = (
        await env.services
          .model("ir.model")
          .search([["model", "=", action.res_model]], { limit: 1 })
      )[0];
      env.services.action.doAction({
        res_model: "ir.model.fields",
        name: description,
        views: [
          [false, "list"],
          [false, "form"],
        ],
        domain: [["model_id", "=", modelId]],
        type: "ir.actions.act_window",
        context: {
          default_model_id: modelId,
        },
      });
    },
    sequence: 120,
  };

  description = env._t("Manage Filters");
  const manageFilters = {
    type: "item",
    description: description,
    callback: () => {
      // manage_filters
      env.services.action.doAction({
        res_model: "ir.filters",
        name: description,
        views: [
          [false, "list"],
          [false, "form"],
        ],
        type: "ir.actions.act_window",
        context: {
          search_default_my_filters: true,
          search_default_model_id: action.res_model,
        },
      });
    },
    sequence: 130,
  };

  const technicalTranslation = {
    type: "item",
    description: env._t("Technical Translation"),
    callback: async () => {
      const result = await env.services
        .model("ir.translation")
        .call("get_technical_translations", [action.res_model]);
      env.services.action.doAction(result);
    },
    sequence: 140,
  };

  const accessSeparator = {
    type: "separator",
    sequence: 200,
  };

  description = env._t("View Access Rights");
  const viewAccessRights = {
    type: "item",
    description: description,
    callback: async () => {
      const modelId = (
        await env.services
          .model("ir.model")
          .search([["model", "=", action.res_model]], { limit: 1 })
      )[0];
      env.services.action.doAction({
        res_model: "ir.model.access",
        name: description,
        views: [
          [false, "list"],
          [false, "form"],
        ],
        domain: [["model_id", "=", modelId]],
        type: "ir.actions.act_window",
        context: {
          default_model_id: modelId,
        },
      });
    },
    sequence: 210,
  };

  description = env._t("Model Record Rules");
  const viewRecordRules = {
    type: "item",
    description: env._t("View Record Rules"),
    callback: async () => {
      const modelId = (
        await env.services
          .model("ir.model")
          .search([["model", "=", action.res_model]], { limit: 1 })
      )[0];
      env.services.action.doAction({
        res_model: "ir.rule",
        name: description,
        views: [
          [false, "list"],
          [false, "form"],
        ],
        domain: [["model_id", "=", modelId]],
        type: "ir.actions.act_window",
        context: {
          default_model_id: modelId,
        },
      });
    },
    sequence: 220,
  };

  const result = [actionSeparator];
  if (action.id) {
    result.push(editAction);
  }
  if (action.res_model) {
    result.push(viewFields);
    result.push(manageFilters);
    result.push(technicalTranslation);
    if (accessRights.canSeeModelAccess || accessRights.canSeeRecordRules) {
      result.push(accessSeparator);
      if (accessRights.canSeeModelAccess) {
        result.push(viewAccessRights);
      }
      if (accessRights.canSeeRecordRules) {
        result.push(viewRecordRules);
      }
    }
  }
  return result;
}

class FieldViewGetDialog extends Component {
  constructor() {
    super(...arguments);
    this.title = this.env._t("Fields View Get");
  }
}
FieldViewGetDialog.template = tags.xml`
  <Dialog title="title">
    <pre t-esc="props.arch"/>
  </Dialog>`;
FieldViewGetDialog.components = { Dialog };

class GetMetadataDialog extends Component {
  constructor(...args) {
    super(...args);
    this.title = this.env._t("View Metadata");
    this.state = useState({});
  }

  async willStart() {
    await this.getMetadata();
  }

  async toggleNoupdate() {
    await this.env.services
      .model("ir.model.data")
      .call("toggle_noupdate", [this.props.res_model, this.state.id]);
    await this.getMetadata();
  }

  async getMetadata() {
    const metadata = (
      await this.env.services
        .model(this.props.res_model)
        .call("get_metadata", [this.props.selectedIds])
    )[0];
    this.state.id = metadata.id;
    this.state.xmlid = metadata.xmlid;
    this.state.creator = formatMany2one(metadata.create_uid);
    this.state.lastModifiedBy = formatMany2one(metadata.write_uid);
    this.state.noupdate = metadata.noupdate;
    const localization = this.env.services.localization;
    this.state.create_date = localization.formatDateTime(
      localization.parseDateTime(metadata.create_date)
    );
    this.state.write_date = localization.formatDateTime(
      localization.parseDateTime(metadata.write_date)
    );
  }
}
GetMetadataDialog.template = "wowl.DebugManager.GetMetadata";
GetMetadataDialog.components = { Dialog };

class SetDefaultDialog extends Component {
  constructor() {
    super(...arguments);
    this.title = this.env._t("Set Default");
    this.state = {
      fieldToSet: "",
      condition: "",
      scope: "self",
    };
    this.dataWidgetState = this.getDataWidgetState();
    this.defaultFields = this.getDefaultFields();
    this.conditions = this.getConditions();
  }

  getDataWidgetState() {
    const renderer = this.props.component.widget.renderer;
    const state = renderer.state;
    const fields = state.fields;
    const fieldsInfo = state.fieldsInfo.form;
    const fieldNamesInView = state.getFieldNames();
    const fieldNamesOnlyOnView = ["message_attachment_count"];
    const fieldsValues = state.data;
    const modifierDatas = {};
    fieldNamesInView.forEach((fieldName) => {
      modifierDatas[fieldName] = renderer.allModifiersData.find((modifierdata) => {
        return modifierdata.node.attrs.name === fieldName;
      });
    });
    return {
      fields,
      fieldsInfo,
      fieldNamesInView,
      fieldNamesOnlyOnView,
      fieldsValues,
      modifierDatas,
      stateId: state.id,
    };
  }

  getDefaultFields() {
    const {
      fields,
      fieldsInfo,
      fieldNamesInView,
      fieldNamesOnlyOnView,
      fieldsValues,
      modifierDatas,
      stateId,
    } = this.dataWidgetState;
    return fieldNamesInView
      .filter((fieldName) => !fieldNamesOnlyOnView.includes(fieldName))
      .map((fieldName) => {
        const modifierData = modifierDatas[fieldName];
        let invisibleOrReadOnly;
        if (modifierData) {
          const evaluatedModifiers = modifierData.evaluatedModifiers[stateId];
          invisibleOrReadOnly = evaluatedModifiers.invisible || evaluatedModifiers.readonly;
        }
        const fieldInfo = fields[fieldName];
        const valueDisplayed = this.display(fieldInfo, fieldsValues[fieldName]);
        const value = valueDisplayed[0];
        const displayed = valueDisplayed[1];
        // ignore fields which are empty, invisible, readonly, o2m
        // or m2m
        if (
          !value ||
          invisibleOrReadOnly ||
          fieldInfo.type === "one2many" ||
          fieldInfo.type === "many2many" ||
          fieldInfo.type === "binary" ||
          fieldsInfo[fieldName].options.isPassword ||
          fieldInfo.depends.length !== 0
        ) {
          return false;
        }
        return {
          name: fieldName,
          string: fieldInfo.string,
          value: value,
          displayed: displayed,
        };
      })
      .filter((val) => val)
      .sort((field) => field.string);
  }

  getConditions() {
    const { fields, fieldNamesInView, fieldsValues } = this.dataWidgetState;
    return fieldNamesInView
      .filter((fieldName) => {
        const fieldInfo = fields[fieldName];
        return fieldInfo.change_default;
      })
      .map((fieldName) => {
        const fieldInfo = fields[fieldName];
        const valueDisplayed = this.display(fieldInfo, fieldsValues[fieldName]);
        const value = valueDisplayed[0];
        const displayed = valueDisplayed[1];
        return {
          name: fieldName,
          string: fieldInfo.string,
          value: value,
          displayed: displayed,
        };
      });
  }

  display(fieldInfo, value) {
    let displayed = value;
    if (value && fieldInfo.type === "many2one") {
      displayed = value.data.display_name;
      value = value.data.id;
    } else if (value && fieldInfo.type === "selection") {
      displayed = fieldInfo.selection.find((option) => {
        return option[0] === value;
      })[1];
    }
    return [value, displayed];
  }

  async saveDefault() {
    if (!this.state.fieldToSet) {
      // TODO $defaults.parent().addClass('o_form_invalid');
      // It doesn't work in web.
      // Good solution: Create a FormView
      return;
    }
    const fieldToSet = this.defaultFields.find((field) => {
      return field.name === this.state.fieldToSet;
    }).value;
    await this.env.services
      .model("ir.default")
      .call("set", [
        this.props.res_model,
        this.state.fieldToSet,
        fieldToSet,
        this.state.scope === "self",
        true,
        this.state.condition || false,
      ]);
    this.trigger("dialog-closed");
  }
}
SetDefaultDialog.template = "wowl.DebugManager.SetDefault";
SetDefaultDialog.components = { Dialog };

export function setupDebugView(accessRights, env, component, action) {
  const viewId = component.props.viewInfo.view_id;
  const viewSeparator = {
    type: "separator",
    sequence: 300,
  };
  const fieldsViewGet = {
    type: "item",
    description: env._t("Fields View Get"),
    callback: () => {
      const props = {
        arch: json_node_to_xml(component.widget.renderer.arch, true, 0),
      };
      env.services.dialog.open(FieldViewGetDialog, props);
    },
    sequence: 340,
  };
  const displayName = action.views
    .find((v) => v.type === component.widget.viewType)
    .name.toString();
  let description = env._t("Edit View: ") + displayName;
  const editView = {
    type: "item",
    description: description,
    callback: () => {
      editModelDebug(env, description, "ir.ui.view", viewId);
    },
    sequence: 350,
  };
  description = env._t("Edit ControlPanelView");
  const editControlPanelView = {
    type: "item",
    description: description,
    callback: () => {
      editModelDebug(
        env,
        description,
        "ir.ui.view",
        component.props.viewParams.action.controlPanelFieldsView.view_id
      );
    },
    sequence: 360,
  };
  const result = [viewSeparator, fieldsViewGet];
  if (accessRights.canEditView) {
    result.push(editView);
    result.push(editControlPanelView);
  }
  return result;
}

export function setupDebugViewForm(env, component, action) {
  const setDefaults = {
    type: "item",
    description: env._t("Set Defaults"),
    callback: () => {
      env.services.dialog.open(SetDefaultDialog, {
        res_model: action.res_model,
        component: component,
      });
    },
    sequence: 310,
  };
  const viewMetadata = {
    type: "item",
    description: env._t("View Metadata"),
    callback: () => {
      const selectedIds = component.widget.getSelectedIds();
      env.services.dialog.open(GetMetadataDialog, {
        res_model: action.res_model,
        selectedIds,
      });
    },
    sequence: 320,
  };
  const description = env._t("Manage Attachments");
  const manageAttachments = {
    type: "item",
    description: description,
    callback: () => {
      const selectedId = component.widget.getSelectedIds()[0];
      env.services.action.doAction({
        res_model: "ir.attachment",
        name: description,
        views: [
          [false, "list"],
          [false, "form"],
        ],
        type: "ir.actions.act_window",
        domain: [
          ["res_model", "=", action.res_model],
          ["res_id", "=", selectedId],
        ],
        context: {
          default_res_model: action.res_model,
          default_res_id: selectedId,
        },
      });
    },
    sequence: 330,
  };
  const result = [setDefaults];
  if (component.widget.getSelectedIds().length === 1) {
    result.push(viewMetadata);
    result.push(manageAttachments);
  }
  return result;
}
