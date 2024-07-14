/** @odoo-module */
import { listView } from "@web/views/list/list_view";
import { computeXpath } from "../xml_utils";
import { registry } from "@web/core/registry";
import { omit } from "@web/core/utils/objects";

import { ListEditorRenderer, columnsStyling } from "./list_editor_renderer";

import { Component, xml } from "@odoo/owl";
import { ListEditorSidebar } from "./list_editor_sidebar/list_editor_sidebar";
import { getStudioNoFetchFields, useModelConfigFetchInvisible } from "../utils";

function parseStudioGroups(node) {
    if (node.hasAttribute("studio_groups")) {
        return node.getAttribute("studio_groups");
    }
}

class EditorArchParser extends listView.ArchParser {
    parse(arch, models, modelName) {
        const parsed = super.parse(...arguments);
        const noFetch = getStudioNoFetchFields(parsed.fieldNodes);
        parsed.fieldNodes = omit(parsed.fieldNodes, ...noFetch.fieldNodes);
        const noFetchFieldNames = noFetch.fieldNames;
        parsed.columns = parsed.columns.filter(
            (col) => col.type !== "field" || !noFetchFieldNames.includes(col.name)
        );
        return parsed;
    }

    parseFieldNode(node, models, modelName) {
        const parsed = super.parseFieldNode(...arguments);
        parsed.studioXpath = computeXpath(node, "list, tree");
        parsed.studio_groups = parseStudioGroups(node);
        return parsed;
    }

    parseWidgetNode(node, models, modelName) {
        const parsed = super.parseWidgetNode(...arguments);
        parsed.studioXpath = computeXpath(node, "list, tree");
        parsed.studio_groups = parseStudioGroups(node);
        return parsed;
    }

    processButton(node) {
        const parsed = super.processButton(node);
        parsed.studioXpath = computeXpath(node, "list, tree");
        parsed.studio_groups = parseStudioGroups(node);
        return parsed;
    }
}

/**
 * X2Many fields can have their subview edited. There are some challenges currently with the RelationalModel
 * - We need to inject the parent record in the evalContext. That way, within the subview's arch
 *   a snippet like `<field name="..." invisible="not parent.id" />` works.
 * - We already know the resIds we have, since we are coming from a x2m. There is no need to search_read them, just to read them
 * - The RelationalModel doesn't really supports creatic staticLists as the root record
 *
 * StaticList supports the two first needs and not DynamicList, we assume that the amount of hacking
 * would be slightly bigger if our starting point is DynamicList. Hence, we choose
 * to extend StaticList instead of DynamicList, and make it the root record of the model.
 */
function useParentedStaticList(model, parentRecord, resIds) {
    const config = model.config;
    config.resIds = resIds;
    config.offset = 0;
    config.limit = Math.max(7, resIds.length); // don't load everything

    model._createRoot = (config, data) => {
        const options = { parent: parentRecord };
        const list = new model.constructor.StaticList(model, { ...config }, data, options);
        list.selection = [];
        return list;
    };
}

class ListEditorController extends listView.Controller {
    setup() {
        super.setup();
        useModelConfigFetchInvisible(this.model);
        if (this.props.parentRecord) {
            useParentedStaticList(this.model, this.props.parentRecord, this.props.resIds);
        }
    }
}
ListEditorController.props = {
    ...listView.Controller.props,
    parentRecord: { type: Object, optional: true },
};

class ControllerShadow extends Component {
    static props = { ...ListEditorController.props };
    get Component() {
        return ListEditorController;
    }

    get componentProps() {
        const props = { ...this.props };
        props.groupBy = [];
        return props;
    }
}
ControllerShadow.template = xml`<t t-component="Component" t-props="componentProps" />`;

const listEditor = {
    ...listView,
    Controller: ControllerShadow,
    ArchParser: EditorArchParser,
    Renderer: ListEditorRenderer,
    props() {
        const props = listView.props(...arguments);
        props.allowSelectors = false;
        props.editable = false;
        props.showButtons = false;
        return props;
    },
    Sidebar: ListEditorSidebar,
};
registry.category("studio_editors").add("list", listEditor);

/**
 *  Drag/Drop styling
 */

const colNearestHookClass = "o_web_studio_nearest_hook";
listEditor.styleNearestHook = function styleNearestColumn(mainRef, nearestHook) {
    const xpath = nearestHook.dataset.xpath;
    const position = nearestHook.dataset.position;
    columnsStyling(
        mainRef.el,
        `.o_web_studio_hook[data-xpath='${xpath}'][data-position='${position}']`,
        [colNearestHookClass]
    );
};

listEditor.styleClickedElement = (mainRef, params) => {
    columnsStyling(mainRef.el, `[data-studio-xpath='${params.xpath}']:not(.o_web_studio_hook)`, [
        "o-web-studio-editor--element-clicked",
    ]);
};
