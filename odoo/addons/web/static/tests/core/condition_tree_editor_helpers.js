/** @odoo-module **/

import { getNodesTextContent, editInput, click, editSelect } from "../helpers/utils";
import { getModelFieldSelectorValues } from "./model_field_selector_tests";
import { fieldService } from "@web/core/field_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { makeFakeLocalizationService } from "../helpers/mock_services";
import { ormService } from "@web/core/orm_service";
import { popoverService } from "@web/core/popover/popover_service";
import { uiService } from "@web/core/ui/ui_service";
import { nameService } from "@web/core/name_service";
import { dialogService } from "@web/core/dialog/dialog_service";
import { datetimePickerService } from "@web/core/datetime/datetimepicker_service";
import { registry } from "@web/core/registry";
import { notificationService } from "@web/core/notifications/notification_service";

export function setupConditionTreeEditorServices() {
    registry.category("services").add("popover", popoverService);
    registry.category("services").add("orm", ormService);
    registry.category("services").add("ui", uiService);
    registry.category("services").add("hotkey", hotkeyService);
    registry.category("services").add("localization", makeFakeLocalizationService());
    registry.category("services").add("field", fieldService);
    registry.category("services").add("name", nameService);
    registry.category("services").add("dialog", dialogService);
    registry.category("services").add("datetime_picker", datetimePickerService);
    registry.category("services").add("notification", notificationService);
}

export function makeServerData() {
    const serverData = {
        models: {
            partner: {
                fields: {
                    foo: { string: "Foo", type: "char", searchable: true },
                    bar: { string: "Bar", type: "boolean", searchable: true },
                    product_id: {
                        string: "Product",
                        type: "many2one",
                        relation: "product",
                        searchable: true,
                    },
                    date: { string: "Date", type: "date", searchable: true },
                    datetime: { string: "Date Time", type: "datetime", searchable: true },
                    int: { string: "Integer", type: "integer", searchable: true },
                    json_field: { string: "Json Field", type: "json", searchable: true },
                    state: {
                        string: "State",
                        type: "selection",
                        selection: [
                            ["abc", "ABC"],
                            ["def", "DEF"],
                            ["ghi", "GHI"],
                        ],
                    },
                },
                records: [
                    { id: 1, foo: "yop", bar: true, product_id: 37 },
                    { id: 2, foo: "blip", bar: true, product_id: false },
                    { id: 4, foo: "abc", bar: false, product_id: 41 },
                ],
                onchanges: {},
            },
            product: {
                fields: {
                    name: { string: "Product Name", type: "char", searchable: true },
                },
                records: [
                    { id: 37, display_name: "xphone" },
                    { id: 41, display_name: "xpad" },
                ],
            },
        },
    };
    return serverData;
}

////////////////////////////////////////////////////////////////////////////////

export const SELECTORS = {
    node: ".o_tree_editor_node",
    row: ".o_tree_editor_row",
    tree: ".o_tree_editor > .o_tree_editor_node",
    connector: ".o_tree_editor_connector",
    condition: ".o_tree_editor_condition",
    addNewRule: ".o_tree_editor_row > a",
    buttonAddNewRule: ".o_tree_editor_node_control_panel > button:nth-child(1)",
    buttonAddBranch: ".o_tree_editor_node_control_panel > button:nth-child(2)",
    buttonDeleteNode: ".o_tree_editor_node_control_panel > button:nth-child(3)",
    pathEditor: ".o_tree_editor_condition > .o_tree_editor_editor:nth-child(1)",
    operatorEditor: ".o_tree_editor_condition > .o_tree_editor_editor:nth-child(2)",
    valueEditor: ".o_tree_editor_condition > .o_tree_editor_editor:nth-child(3)",
    editor: ".o_tree_editor_editor",
    clearNotSupported: ".o_input .fa-times",
    tag: ".o_input .o_tag",
    toggleArchive: ".form-switch",
    complexCondition: ".o_tree_editor_complex_condition",
    complexConditionInput: ".o_tree_editor_complex_condition input",
};

const CHILD_SELECTOR = ["connector", "condition", "complexCondition"]
    .map((k) => SELECTORS[k])
    .join(",");
export function getTreeEditorContent(target, options = {}) {
    const content = [];
    const nodes = target.querySelectorAll(SELECTORS.node);
    const mapping = new Map();
    for (const node of nodes) {
        const parent = node.parentElement.closest(SELECTORS.node);
        const level = parent ? mapping.get(parent) + 1 : 0;
        mapping.set(node, level);
        const nodeValue = { level };
        const associatedNode = node.querySelector(CHILD_SELECTOR);
        const className = associatedNode.className;
        if (className.includes("connector")) {
            nodeValue.value = getCurrentConnector(node);
        } else if (className.includes("complex_condition")) {
            nodeValue.value = getCurrentComplexCondition(node);
        } else {
            nodeValue.value = getCurrentCondition(node);
        }
        if (options.node) {
            nodeValue.node = node;
        }
        content.push(nodeValue);
    }
    return content;
}

export function get(target, selector, index = 0) {
    if (index) {
        return [...target.querySelectorAll(selector)].at(index);
    }
    return target.querySelector(selector);
}

function getValue(target) {
    if (target) {
        const el = target.querySelector("input,select,span:not(.o_tag)");
        switch (el.tagName) {
            case "INPUT":
                return el.value;
            case "SELECT":
                return el.options[el.selectedIndex].label;
            case "SPAN":
                return el.innerText;
        }
    }
}

export function getCurrentPath(target, index = 0) {
    const pathEditor = get(target, SELECTORS.pathEditor, index);
    if (pathEditor) {
        if (pathEditor.querySelector(".o_model_field_selector")) {
            return getModelFieldSelectorValues(pathEditor).join(" > ");
        }
        return pathEditor.textContent;
    }
}

export function getCurrentOperator(target, index = 0) {
    const operatorEditor = get(target, SELECTORS.operatorEditor, index);
    return getValue(operatorEditor);
}

export function getCurrentValue(target, index) {
    const valueEditor = get(target, SELECTORS.valueEditor, index);
    const value = getValue(valueEditor);
    if (valueEditor) {
        const tags = [...valueEditor.querySelectorAll(".o_tag")];
        if (tags.length) {
            let text = `${tags.map((t) => t.innerText).join(" ")}`;
            if (value) {
                text += ` ${value}`;
            }
            return text;
        }
    }
    return value;
}

export function getOperatorOptions(target, index = 0) {
    const el = get(target, SELECTORS.operatorEditor, index);
    if (el) {
        const select = el.querySelector("select");
        return [...select.options].map((o) => o.label);
    }
}

export function getValueOptions(target, index = 0) {
    const el = get(target, SELECTORS.valueEditor, index);
    if (el) {
        const select = el.querySelector("select");
        return [...select.options].map((o) => o.label);
    }
}

function getCurrentComplexCondition(target, index = 0) {
    const input = get(target, SELECTORS.complexConditionInput, index);
    return input?.value;
}

export function getConditionText(target, index = 0) {
    const condition = get(target, SELECTORS.condition, index);
    if (condition) {
        const texts = [];
        for (const t of getNodesTextContent(condition.childNodes)) {
            const t2 = t.trim();
            if (t2) {
                texts.push(t2);
            }
        }
        return texts.join(" ");
    }
}

function getCurrentCondition(target, index = 0) {
    const values = [getCurrentPath(target, index), getCurrentOperator(target, index)];
    const valueEditor = get(target, SELECTORS.valueEditor, index);
    if (valueEditor) {
        values.push(getCurrentValue(target, index));
    }
    return values;
}

function getCurrentConnector(target, index = 0) {
    const connector = get(
        target,
        `${SELECTORS.connector} .dropdown-toggle, ${SELECTORS.connector} > span:nth-child(2), ${SELECTORS.connector} > span > strong`,
        index
    );
    return connector?.textContent.search("all") >= 0 ? "all" : connector?.textContent;
}

////////////////////////////////////////////////////////////////////////////////

export function isNotSupportedPath(target, index = 0) {
    const pathEditor = get(target, SELECTORS.pathEditor, index);
    return Boolean(pathEditor.querySelector(SELECTORS.clearNotSupported));
}

export function isNotSupportedOperator(target, index = 0) {
    const operatorEditor = get(target, SELECTORS.operatorEditor, index);
    return Boolean(operatorEditor.querySelector(SELECTORS.clearNotSupported));
}

export function isNotSupportedValue(target, index = 0) {
    const valueEditor = get(target, SELECTORS.valueEditor, index);
    return Boolean(valueEditor.querySelector(SELECTORS.clearNotSupported));
}

////////////////////////////////////////////////////////////////////////////////

export async function selectOperator(target, operator, index = 0) {
    const el = get(target, SELECTORS.operatorEditor, index);
    await editSelect(el, "select", JSON.stringify(operator));
}

export async function selectValue(target, value, index = 0) {
    const el = get(target, SELECTORS.valueEditor, index);
    await editSelect(el, "select", JSON.stringify(value));
}

export async function editValue(target, value, index = 0) {
    const el = get(target, SELECTORS.valueEditor, index);
    await editInput(el, "input", value);
}

export async function clickOnButtonAddNewRule(target, index = 0) {
    await click(get(target, SELECTORS.buttonAddNewRule, index));
}

export async function clickOnButtonAddBranch(target, index = 0) {
    await click(get(target, SELECTORS.buttonAddBranch, index));
}

export async function clickOnButtonDeleteNode(target, index = 0) {
    await click(get(target, SELECTORS.buttonDeleteNode, index));
}

export async function clearNotSupported(target, index = 0) {
    await click(get(target, SELECTORS.clearNotSupported, index));
}

export async function addNewRule(target) {
    await click(target, SELECTORS.addNewRule);
}

export async function toggleArchive(target) {
    await click(target, SELECTORS.toggleArchive);
}

////////////////////////////////////////////////////////////////////////////////
