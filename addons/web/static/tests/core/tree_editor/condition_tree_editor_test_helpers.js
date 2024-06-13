import { queryAll, queryAllTexts, queryOne, queryText } from "@odoo/hoot-dom";
import { contains, fields, models } from "@web/../tests/web_test_helpers";

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

export function getTreeEditorContent(options = {}) {
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
        if (options.node) {
            nodeValue.node = node;
        }
        content.push(nodeValue);
    }
    return content;
}

export function get(selector, index, root) {
    return queryAll(selector, { root }).at(index || 0);
}

function getValue(root) {
    if (root) {
        const el = queryOne("input,select,span:not(.o_tag)", { root });
        switch (el.tagName) {
            case "INPUT":
                return el.value;
            case "SELECT":
                return el.options[el.selectedIndex].label;
            default:
                return el.innerText;
        }
    }
}

export function getCurrentPath(index, target) {
    const pathEditor = get(SELECTORS.pathEditor, index, target);
    if (pathEditor) {
        if (pathEditor.querySelector(".o_model_field_selector")) {
            return getModelFieldSelectorValues(pathEditor).join(" > ");
        }
        return pathEditor.innerText;
    }
}

export function getCurrentOperator(index, target) {
    const operatorEditor = get(SELECTORS.operatorEditor, index, target);
    return getValue(operatorEditor);
}

export function getCurrentValue(index, target) {
    const valueEditor = get(SELECTORS.valueEditor, index, target);
    const value = getValue(valueEditor);
    if (valueEditor) {
        const tags = queryAll(".o_tag", { root: valueEditor });
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

export function getOperatorOptions(index, target) {
    const el = get(SELECTORS.operatorEditor, index, target);
    if (el) {
        const select = queryOne("select", { root: el });
        return [...select.options].map((o) => o.label);
    }
}

export function getValueOptions(index, target) {
    const el = get(SELECTORS.valueEditor, index, target);
    if (el) {
        const select = queryOne("select", { root: el });
        return [...select.options].map((o) => o.label);
    }
}

function getCurrentComplexCondition(index, target) {
    const input = get(SELECTORS.complexConditionInput, index, target);
    return input?.value;
}

export function getConditionText(index, target) {
    const condition = get(SELECTORS.condition, index, target);
    return queryText(condition).replace(/\n/g, " ");
}

function getCurrentCondition(index, target) {
    const values = [getCurrentPath(index, target), getCurrentOperator(index, target)];
    const valueEditor = get(SELECTORS.valueEditor, index, target);
    if (valueEditor) {
        values.push(getCurrentValue(index, target));
    }
    return values;
}

function getCurrentConnector(index, target) {
    const connectorText = queryText(
        get(
            `${SELECTORS.connector} .dropdown-toggle, ${SELECTORS.connector} > span:nth-child(2), ${SELECTORS.connector} > span > strong`,
            index,
            target
        )
    );
    return connectorText.includes("all") ? "all" : connectorText;
}

////////////////////////////////////////////////////////////////////////////////

export function isNotSupportedPath(index, target) {
    const pathEditor = get(SELECTORS.pathEditor, index, target);
    return Boolean(queryOne(SELECTORS.clearNotSupported, { root: pathEditor }));
}

export function isNotSupportedOperator(index, target) {
    const operatorEditor = get(SELECTORS.operatorEditor, index, target);
    return Boolean(queryOne(SELECTORS.clearNotSupported, { root: operatorEditor }));
}

export function isNotSupportedValue(index, target) {
    const valueEditor = get(SELECTORS.valueEditor, index, target);
    return Boolean(queryOne(SELECTORS.clearNotSupported, { root: valueEditor }));
}

////////////////////////////////////////////////////////////////////////////////

export async function selectOperator(operator, index, target) {
    await contains(get(SELECTORS.operatorEditor + " select", index, target)).select(
        JSON.stringify(operator)
    );
}

export async function selectValue(value, index, target) {
    await contains(get(SELECTORS.valueEditor + " select", index, target)).select(
        JSON.stringify(value)
    );
}

export async function editValue(value, options, index, target) {
    await contains(get(SELECTORS.valueEditor + " input", index, target)).edit(value, options);
}

export async function clickOnButtonAddNewRule(index, target) {
    await contains(get(SELECTORS.buttonAddNewRule, index, target)).click();
}

export async function clickOnButtonAddBranch(index, target) {
    await contains(get(SELECTORS.buttonAddBranch, index, target)).click();
}

export async function clickOnButtonDeleteNode(index, target) {
    await contains(get(SELECTORS.buttonDeleteNode, index, target)).click();
}

export async function clearNotSupported(index, target) {
    await contains(get(SELECTORS.clearNotSupported, index, target)).click();
}

export async function addNewRule() {
    await contains(SELECTORS.addNewRule).click();
}

export async function toggleArchive() {
    await contains(SELECTORS.toggleArchive).click();
}

////////////////////////////////////////////////////////////////////////////////

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

export async function followRelation(index = 0) {
    await contains(`.o_model_field_selector_popover_item_relation:eq(${index})`).click();
}

export function getFocusedFieldName() {
    return queryText(".o_model_field_selector_popover_item.active");
}
