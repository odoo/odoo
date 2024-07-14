/** @odoo-module */
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import {
    computeXpath,
    getNodesFromXpath,
} from "@web_studio/client_action/view_editor/editors/xml_utils";
import { visitXML } from "@web/core/utils/xml";
import { StudioHook } from "@web_studio/client_action/view_editor/editors/components/studio_hook_component";
import { InteractiveEditorSidebar } from "@web_studio/client_action/view_editor/interactive_editor/interactive_editor_sidebar";
import { ExistingFields } from "@web_studio/client_action/view_editor/view_structures/view_structures";
import { Property } from "@web_studio/client_action/view_editor/property/property";
import { SidebarViewToolbox } from "@web_studio/client_action/view_editor/interactive_editor/sidebar_view_toolbox/sidebar_view_toolbox";
import { _t } from "@web/core/l10n/translation";
import { memoize } from "@web/core/utils/functions";
import { useOwnedDialogs } from "@web/core/utils/hooks";
import { SidebarPropertiesToolbox } from "@web_studio/client_action/view_editor/interactive_editor/properties/sidebar_properties_toolbox/sidebar_properties_toolbox";
import { standardViewProps } from "@web/views/standard_view_props";

function getGroupByFieldNameFromString(str) {
    const matches = str.match(/(,\s*)?(["'])group_by\2\1(\s*:\s*)?\2(?<fieldName>.*)\2/);
    if (!matches) {
        return null;
    }
    if (!matches.groups) {
        return null;
    }
    return matches.groups.fieldName;
}

function isFilterGroupBy(node) {
    if (!node.hasAttribute("context")) {
        return false;
    }
    if (/(['"])group_by\1\s*:/.test(node.getAttribute("context"))) {
        return true;
    }
    return false;
}

/** CONTROLLER STUFF */
class SearchEditorArchParser {
    parse(xmlDoc) {
        this.fields = [];
        this.filters = [];
        this.groupBys = [];
        this.currentCategory = null;
        this.currentItems = { items: [] };

        visitXML(xmlDoc, this.visitNode.bind(this));
        this.changeCategory(null, true); // Flush

        return {
            fields: this.fields,
            filters: this.filters,
            groupBys: this.groupBys,
            xmlDoc,
        };
    }

    visitNode(node) {
        if (node.nodeType !== 1) {
            return;
        }

        const nodeName = node.nodeName;
        const studioXpath = computeXpath(node, "search");
        if (nodeName === "field") {
            this.changeCategory("field", true);
            const item = this.parseNode(node);
            item.studioXpath = studioXpath;
            this.fields.push(item);
            return false;
        }
        if (nodeName === "filter") {
            const category = isFilterGroupBy(node) ? "groupBy" : "filter";
            this.changeCategory(category);
            const item = this.parseNode(node);
            item.studioXpath = studioXpath;
            this.pushItem(item);
            return false;
        }
        if (nodeName === "separator") {
            this.changeCategory("filter", true);
            this.currentItems.separator = studioXpath;
            return false;
        }
        if (nodeName === "group") {
            this.changeCategory(null, true);
            Array.from(node.children).forEach(this.visitNode.bind(this));
            this.changeCategory(null, true);
            return false;
        }
    }

    parseNode(node) {
        const nodeName = node.nodeName;
        const invisible = node.getAttribute("invisible");
        if (nodeName === "field") {
            return {
                type: "field",
                name: node.getAttribute("name"),
                label: node.getAttribute("string"),
                invisible,
            };
        }
        if (nodeName === "separator") {
            return { type: "separator" };
        }
        if (nodeName === "filter") {
            const item = {
                type: "filter",
                name: node.getAttribute("name"),
                label: node.getAttribute("string") || node.getAttribute("help"),
                domain: node.getAttribute("domain"),
                invisible,
            };
            if (node.hasAttribute("context")) {
                const groupBy = getGroupByFieldNameFromString(node.getAttribute("context"));
                if (groupBy) {
                    item.groupBy = groupBy;
                    item.type = "groupBy";
                }
            }
            return item;
        }
    }

    pushItem(item) {
        this.currentItems.items.push(item);
    }

    changeCategory(category, force) {
        if (this.currentCategory !== category || force) {
            let itemsToPushIn;
            if (this.currentCategory === "filter") {
                itemsToPushIn = this.filters;
            } else if (this.currentCategory === "groupBy") {
                itemsToPushIn = this.groupBys;
            }
            if (itemsToPushIn) {
                itemsToPushIn.push(this.currentItems);
                this.currentItems = { items: [] };
            }
        }
        this.currentCategory = category || this.currentCategory;
    }
}

class SearchEditorController extends Component {
    static props = { ...standardViewProps, archInfo: { type: Object } };
    static template = "web_studio.SearchEditorController";
    static components = { StudioHook };

    setup() {
        this.viewEditorModel = useState(this.env.viewEditorModel);
    }

    get filtersGroups() {
        return this.props.archInfo.filters;
    }

    hasItems(group) {
        return group.some((g) => this.getItems(g.items));
    }

    get autoCompleteFields() {
        return this.props.archInfo.fields;
    }

    get groupByGroups() {
        return this.props.archInfo.groupBys;
    }

    getItems(items) {
        if (!this.viewEditorModel.showInvisible) {
            return items.filter((i) => i.invisible !== "True" && i.invisible !== "1");
        }
        return items;
    }

    getFirstHookProps(type) {
        const xpath = "/search";
        const position = "inside";

        const group = type === "filter" ? this.filtersGroups : this.groupByGroups;
        if (this.hasItems(group)) {
            return false;
        }
        const props = {
            xpath,
            position,
            type,
        };
        if (type === "groupBy") {
            props.infos = JSON.stringify({
                create_group: true,
            });
        }
        return props;
    }

    getItemLabel(type, item) {
        if (type === "filter") {
            return item.label;
        }
        if (type === "groupBy") {
            let label = item.label || item.name;
            if (this.env.debug) {
                label = `${label} (${item.groupBy})`;
            }
            return label;
        }
        if (type === "field") {
            let label = item.label || this.props.fields[item.name].string;
            if (this.env.debug) {
                label = `${label} (${item.name})`;
            }
            return label;
        }
    }

    onItemClicked(ev, xpath) {
        this.env.config.onNodeClicked(xpath);
    }
}

/** SIDEBAR STUFF */

class SearchComponents extends Component {
    static props = {};
    static template = "web_studio.SearchEditor.Sidebar.Components";

    get structures() {
        return {
            filter: {
                name: _t("Filter"),
                class: "o_web_studio_filter",
            },
            separator: {
                name: _t("Separator"),
                class: "o_web_studio_filter_separator",
            },
        };
    }
}

class SimpleElementEditor extends Component {
    static props = { node: { type: Object } };
    static components = { Property, SidebarPropertiesToolbox };
    static template = "web_studio.SearchEditor.SimpleElementEditor";

    setup() {
        this.addDialog = useOwnedDialogs();
    }

    get viewEditorModel() {
        return this.env.viewEditorModel;
    }

    get node() {
        return this.props.node;
    }

    get label() {
        if (this.node.type === "field" && !this.node.label) {
            return this.env.viewEditorModel.fields[this.node.name].string;
        }
        return this.node.label;
    }

    get domain() {
        if (this.node.type === "filter") {
            return this.node.domain;
        }
        return null;
    }

    onChangeDomain(value) {
        const operation = {
            new_attrs: { domain: value },
            type: "attributes",
            position: "attributes",
            target: this.viewEditorModel.getFullTarget(this.viewEditorModel.activeNodeXpath),
        };
        this.viewEditorModel.doOperation(operation);
    }

    onChangeLabel(value) {
        const operation = {
            new_attrs: { string: value },
            type: "attributes",
            position: "attributes",
            target: this.viewEditorModel.getFullTarget(this.viewEditorModel.activeNodeXpath),
        };
        this.viewEditorModel.doOperation(operation);
    }

    onPropertyRemoved() {
        const activeNodeXpath = this.viewEditorModel.activeNodeXpath;
        this.viewEditorModel.activeNodeXpath = null;
        const operation = {
            type: "remove",
            target: this.viewEditorModel.getFullTarget(activeNodeXpath),
        };
        this.viewEditorModel.doOperation(operation);
    }
}

class SearchEditorSidebar extends Component {
    static template = "web_studio.ViewEditor.SearchEditorSidebar";
    static props = {
        openViewInForm: { type: Function, optional: true },
        openDefaultValues: { type: Function, optional: true },
    };
    static components = {
        InteractiveEditorSidebar,
        ExistingFields,
        SearchComponents,
        Property,
        SidebarViewToolbox,
        SimpleElementEditor,
    };

    setup() {
        this.viewEditorModel = useState(this.env.viewEditorModel);
        const searchArchParser = new SearchEditorArchParser();
        this._getCurrentNode = memoize(() => {
            const { activeNodeXpath, xmlDoc } = this.viewEditorModel;
            if (!activeNodeXpath) {
                return null;
            }
            const node = getNodesFromXpath(activeNodeXpath, xmlDoc);
            return searchArchParser.parseNode(node[0]);
        });
    }

    get currentNode() {
        const { activeNodeXpath, arch } = this.viewEditorModel;
        return this._getCurrentNode(`${activeNodeXpath}_${arch}`);
    }
}

/** SIDEBAR STUFF */
const searchEditor = {
    ArchParser: SearchEditorArchParser,
    Controller: SearchEditorController,
    props(genericProps, editor, config) {
        const archInfo = new editor.ArchParser().parse(genericProps.arch);
        return { ...genericProps, archInfo };
    },
    Sidebar: SearchEditorSidebar,
};

registry.category("studio_editors").add("search", searchEditor);

/** Drag/Drop */

const FILTER_TYPES = ["date", "datetime"];
const GROUPABLE_TYPES = [
    "many2one",
    "many2many",
    "char",
    "boolean",
    "selection",
    "date",
    "datetime",
];

function fieldCanBeFilter(field) {
    return FILTER_TYPES.includes(field.type) && field.store;
}

function fieldCanBeGroupable(field) {
    return GROUPABLE_TYPES.includes(field.type) && field.store;
}

const disabledDropClass = "o-web-studio-search--drop-disable";

searchEditor.isValidHook = function isValidSearchHook({ hook, element, viewEditorModel }) {
    if (hook.closest(`.${disabledDropClass}`)) {
        return false;
    }
    return true;
};

searchEditor.prepareForDrag = function ({ element, viewEditorModel, ref }) {
    const draggingStructure = element.dataset.structure;

    switch (draggingStructure) {
        case "field": {
            const fieldName = JSON.parse(element.dataset.drop).fieldName;
            const field = viewEditorModel.fields[fieldName];
            if (!fieldCanBeFilter(field)) {
                ref.el
                    .querySelector(`.o-web-studio-search--filters`)
                    .classList.add(disabledDropClass);
            }
            if (!fieldCanBeGroupable(field)) {
                ref.el
                    .querySelector(`.o-web-studio-search--groupbys`)
                    .classList.add(disabledDropClass);
            }

            break;
        }
        case "separator":
        case "filter": {
            const els = ref.el.querySelectorAll(
                ".o-web-studio-search--fields,.o-web-studio-search--groupbys"
            );
            els.forEach((el) => el.classList.add("o-web-studio-search--drop-disable"));
            break;
        }
    }

    return () => {
        ref.el
            .querySelectorAll(".o-web-studio-search--drop-disable")
            .forEach((el) => el.classList.remove("o-web-studio-search--drop-disable"));
    };
};
