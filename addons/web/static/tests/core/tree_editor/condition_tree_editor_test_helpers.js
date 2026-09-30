import { queryAll, queryAllTexts, queryOne, queryText, queryValue } from "@odoo/hoot-dom";
import { contains, fields, models } from "@web/../tests/web_test_helpers";

import { Domain } from "@web/core/domain";
import { formatAST, parseExpr } from "@web/core/py_js/py";

export function label(operator, fieldType) {
    switch (operator) {
        case "=":
            if (["many2one", "many2many", "one2many"].includes(fieldType)) {
                return "=";
            }
            return "is equal to";
        case "!=":
            if (["many2one", "many2many", "one2many"].includes(fieldType)) {
                return "!=";
            }
            return "is not equal to";
        case "in":
            if (["many2one", "many2many", "one2many"].includes(fieldType)) {
                return "is equal to";
            }
            return "is in";
        case "not in":
            if (["many2one", "many2many", "one2many"].includes(fieldType)) {
                return "is not equal to";
            }
            return "is not in";
        case ">":
            if (["date", "datetime"].includes(fieldType)) {
                return "after";
            }
            return "greater than";
        case "<":
            if (["date", "datetime"].includes(fieldType)) {
                return "before";
            }
            return "lower than";
        case "ilike":
            return "contains";
        case "not ilike":
            return "does not contain";
        case "<=":
            return "lower or equal to";
        case ">=":
            return "greater or equal to";
        case "set":
            return "is set";
        case "not set":
            return "is not set";
        case "in range":
            return "is in";
        case "between":
            return "between";
        case "starts with":
            return "starts with";
    }
}

export function formatDomain(str) {
    return new Domain(str).toString();
}

export function formatExpr(str) {
    return formatAST(parseExpr(str));
}

/**
 * @typedef {import("@odoo/hoot-dom").FillOptions} FillOptions
 * @typedef {import("@odoo/hoot-dom").Target} Target
 */

function getValue(root) {
    if (!root) {
        return null;
    }
    const el = queryOne("input,select,span:not(.o_tag):not(.o_dropdown_button)", { root });
    switch (el.tagName) {
        case "INPUT":
            return queryValue(el);
        case "SELECT":
            return el.options[el.selectedIndex].label;
        default:
            return queryText(el);
    }
}

/**
 * @param {Target} selector
 * @param {number} [index]
 * @param {Target} [root]
 */
function queryAt(selector, index, root) {
    return queryAll(selector, { root }).at(index || 0);
}

export class Partner extends models.Model {
    foo = fields.Char();
    bar = fields.Boolean();
    name = fields.Char({ string: "Partner Name" });
    product_id = fields.Many2one({ relation: "product" });
    int = fields.Integer();
    date = fields.Date();
    datetime = fields.Datetime();
    json_field = fields.Json({ string: "Json Field" });
    state = fields.Selection({
        selection: [
            ["abc", "ABC"],
            ["def", "DEF"],
            ["ghi", "GHI"],
        ],
    });

    _records = [
        { id: 1, foo: "yop", bar: true, product_id: 37, name: "first record" },
        { id: 2, foo: "blip", bar: true, product_id: false, name: "second record" },
        { id: 4, foo: "abc", bar: false, product_id: 41, name: "aaa" },
    ];
}

export class Product extends models.Model {
    name = fields.Char({ string: "Product Name" });
    bar = fields.Boolean({ string: "Product Bar" });
    team_id = fields.Many2one({
        string: "Product Team",
        relation: "team",
        searchable: true,
    });

    _records = [
        { id: 37, name: "xphone" },
        { id: 41, name: "xpad" },
    ];
}

export class Team extends models.Model {
    name = fields.Char({ string: "Team Name", searchable: true });
    player_ids = fields.One2many({ relation: "player", string: "Players" });

    _records = [
        { id: 1, display_name: "Mancester City" },
        { id: 2, display_name: "Arsenal" },
    ];
}

export class Player extends models.Model {
    name = fields.Char({ string: "Player Name", searchable: true });
    country_id = fields.Many2one({ string: "Country", relation: "country" });
    _records = [
        { id: 1, name: "Kevin De Bruyne" },
        { id: 2, name: "Jeremy Doku" },
    ];
}

export class Country extends models.Model {
    foo = fields.Char();
    stage_id = fields.Many2one({ relation: "stage" });
}

export class Stage extends models.Model {
    bar = fields.Boolean();
}

export const SELECTORS = {
    node: ".o_tree_editor_node",
    row: ".o_tree_editor_row",
    tree: ".o_tree_editor > .o_tree_editor_node",
    connector: ".o_tree_editor_connector",
    connectorValue: ".o_tree_editor_connector .o_tree_editor_connector_value",
    connectorToggler: ".o_tree_editor_connector .o_tree_editor_connector_value button.o-dropdown",
    condition: ".o_tree_editor_condition",
    addNewRule: ".o_tree_editor_row > a",
    buttonAddNewRule: ".o_tree_editor_node_control_panel > button[data-tooltip='Add rule']",
    buttonAddBranch: ".o_tree_editor_node_control_panel > button[data-tooltip='Add nested rule']",
    buttonDeleteNode: ".o_tree_editor_node_control_panel > button[data-tooltip='Delete rule']",
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

export function getTreeEditorContent() {
    const content = [];
    const nodes = queryAll(SELECTORS.node);
    const mapping = new Map();
    for (const node of nodes) {
        const parent = node.parentElement.closest(SELECTORS.node);
        const level = parent ? mapping.get(parent) + 1 : 0;
        mapping.set(node, level);
        const nodeValue = { level };
        const associatedNode = node.querySelector(CHILD_SELECTOR);
        const className = associatedNode.className;
        if (className.includes("connector")) {
            nodeValue.value = getCurrentConnector(0, node);
        } else if (className.includes("complex_condition")) {
            nodeValue.value = getCurrentComplexCondition(0, node);
        } else {
            nodeValue.value = getCurrentCondition(0, node);
        }
        content.push(nodeValue);
    }
    return content;
}

/**
 * @param {number} [index=0]
 * @param {Target} [target]
 */
export function getCurrentPath(index, target) {
    const pathEditor = queryAt(SELECTORS.pathEditor, index, target);
    if (pathEditor) {
        if (pathEditor.querySelector(".o_model_field_selector")) {
            return getModelFieldSelectorValues(pathEditor).join(" > ");
        }
        return queryText(pathEditor);
    }
}

/**
 * @param {number} [index=0]
 * @param {Target} [target]
 */
export function getCurrentOperator(index, target) {
    const operatorEditor = queryAt(SELECTORS.operatorEditor, index, target);
    return getValue(operatorEditor);
}

/**
 * @param {number} [index=0]
 * @param {Target} [target]
 */
export function getCurrentValue(index, target) {
    const valueEditor = queryAt(SELECTORS.valueEditor, index, target);
    const value = getValue(valueEditor);
    if (valueEditor) {
        const texts = queryAllTexts(`.o_tag`, { root: valueEditor });
        if (texts.length) {
            if (value) {
                texts.push(value);
            }
            return texts.join(" ");
        }
    }
    return value;
}

/**
 * @param {number} [index=0]
 * @param {Target} [target]
 */
export function getOperatorOptions(index, target) {
    const el = queryAt(SELECTORS.operatorEditor, index, target);
    if (el) {
        return queryAll(`select:only option`, { root: el }).map((o) => o.label);
    }
}

/**
 * @param {number} [index=0]
 * @param {Target} [target]
 */
export function getValueOptions(index, target) {
    const el = queryAt(SELECTORS.valueEditor, index, target);
    if (el) {
        return queryAll(`select:only option`, { root: el }).map((o) => o.label);
    }
}

/**
 * @param {number} [index=0]
 * @param {Target} [target]
 */
function getCurrentComplexCondition(index, target) {
    const input = queryAt(SELECTORS.complexConditionInput, index, target);
    return input?.value;
}

/**
 * @param {number} [index=0]
 * @param {Target} [target]
 */
export function getConditionText(index, target) {
    const condition = queryAt(SELECTORS.condition, index, target);
    return queryText(condition).replace(/\n/g, " ");
}

/**
 * @param {number} [index=0]
 * @param {Target} [target]
 */
function getCurrentCondition(index, target) {
    const values = [getCurrentPath(index, target), getCurrentOperator(index, target)];
    const valueEditor = queryAt(SELECTORS.valueEditor, index, target);
    if (valueEditor) {
        values.push(getCurrentValue(index, target));
    }
    return values;
}

/**
 * @param {number} [index=0]
 * @param {Target} [target]
 */
function getCurrentConnector(index, target) {
    const connectorText = queryAllTexts(
        `${SELECTORS.connector} > div > span > strong, ${SELECTORS.connectorValue}`,
        { root: target }
    ).at(index);
    return connectorText.includes("all") ? "all" : connectorText;
}

////////////////////////////////////////////////////////////////////////////////

/**
 * @param {number} [index=0]
 * @param {Target} [target]
 */
export function isNotSupportedPath(index, target) {
    const pathEditor = queryAt(SELECTORS.pathEditor, index, target);
    return Boolean(queryOne(SELECTORS.clearNotSupported, { root: pathEditor }));
}

/**
 * @param {number} [index=0]
 * @param {Target} [target]
 */
export function isNotSupportedOperator(index, target) {
    const operatorEditor = queryAt(SELECTORS.operatorEditor, index, target);
    return Boolean(queryOne(SELECTORS.clearNotSupported, { root: operatorEditor }));
}

/**
 * @param {number} [index=0]
 * @param {Target} [target]
 */
export function isNotSupportedValue(index, target) {
    const valueEditor = queryAt(SELECTORS.valueEditor, index, target);
    return Boolean(queryOne(SELECTORS.clearNotSupported, { root: valueEditor }));
}

////////////////////////////////////////////////////////////////////////////////

/**
 * @param {number} [index=0]
 * @param {Target} [target]
 */
export async function toggleConnector(index, target) {
    await contains(queryAt(SELECTORS.connectorToggler, index, target)).click();
}

/**
 * @param {any} operator
 * @param {number} [index=0]
 * @param {Target} [target]
 */
export async function selectOperator(operator, index, target) {
    await contains(`${SELECTORS.operatorEditor}:eq(${index || 0}) select`, { root: target }).select(
        JSON.stringify(operator)
    );
}

/**
 * @param {any} value
 * @param {number} [index=0]
 * @param {Target} [target]
 */
export async function selectValue(value, index, target) {
    await contains(`${SELECTORS.valueEditor}:eq(${index || 0}) select`, { root: target }).select(
        JSON.stringify(value)
    );
}

/**
 * @param {any} value
 * @param {FillOptions} [options]
 * @param {number} [index=0]
 * @param {Target} [target]
 */
export async function editValue(value, options, index, target) {
    await contains(`${SELECTORS.valueEditor}:eq(${index || 0}) input`, { root: target }).edit(
        value,
        options
    );
}

/**
 * @param {number} [index=0]
 * @param {Target} [target]
 */
export async function clickOnButtonAddRule(index, target) {
    await contains(queryAt(SELECTORS.buttonAddNewRule, index, target)).click();
}

/**
 * @param {number} [index=0]
 * @param {Target} [target]
 */
export async function clickOnButtonAddBranch(index, target) {
    await contains(queryAt(SELECTORS.buttonAddBranch, index, target)).click();
}

/**
 * @param {number} [index=0]
 * @param {Target} [target]
 */
export async function clickOnButtonDeleteNode(index, target) {
    await contains(queryAt(SELECTORS.buttonDeleteNode, index, target)).click();
}

/**
 * @param {number} [index=0]
 * @param {Target} [target]
 */
export async function clearNotSupported(index, target) {
    await contains(queryAt(SELECTORS.clearNotSupported, index, target)).click();
}

export async function addNewRule(index, target) {
    await contains(queryAt(SELECTORS.addNewRule, index, target)).click();
}

export async function toggleArchive() {
    await contains(SELECTORS.toggleArchive).click();
}

////////////////////////////////////////////////////////////////////////////////

/**
 * @param {number} [index=0]
 */
export async function openModelFieldSelectorPopover(index = 0) {
    await contains(`.o_model_field_selector:eq(${index})`).click();
}

export function getModelFieldSelectorValues(root) {
    return queryAllTexts("span.o_model_field_selector_chain_part", { root });
}

export function getDisplayedFieldNames() {
    return queryAllTexts(".o_model_field_selector_popover_item_name");
}

export function getTitle() {
    return queryText(".o_model_field_selector_popover .o_model_field_selector_popover_title");
}

export async function clickPrev() {
    await contains(".o_model_field_selector_popover_prev_page").click();
}

/**
 * @param {number} [index=0]
 * @param {Target} [target]
 */
export async function followRelation(index, target) {
    await contains(queryAt(".o_model_field_selector_popover_item_relation", index, target)).click();
}

export function getFocusedFieldName() {
    return queryText(".o_model_field_selector_popover_item.active");
}
