/** @odoo-module native */

import { _t } from "@web/core/translation";

const NAME_LIMIT = 24;
const COLUMN_GAP = 90;
const ROW_GAP = 40;

// Ordered as they are offered on a step's right edge, most common first.
export const CONDITIONS = [
    "on_success",
    "on_error",
    "always",
    "expression",
    "event",
    "no_event",
];

// An `expression` edge carries a Python expression, and an event edge an event
// code, that the canvas cannot ask for; `workflow.edge` refuses either without
// it, so those ports are only ever shown for an edge that already exists.
const DRAGGABLE_CONDITIONS = ["on_success", "on_error", "always"];

export const INPUT_PORT_ID = "in";
const PORT_KIND = "step";

export function canConnect(edges, sourceId, targetId) {
    if (!sourceId || !targetId || sourceId === targetId) {
        return false;
    }
    return !edges.some((edge) => edge.source === sourceId && edge.target === targetId);
}

export function nodeClasses(node) {
    const classes = ["o_workflow_canvas_node"];
    if (node.node_type && node.node_type !== "action") {
        classes.push(`o_workflow_canvas_type_${node.node_type}`);
    }
    if (node.runtime_state) {
        classes.push(`o_workflow_canvas_run_${node.runtime_state}`);
    }
    return classes.join(" ");
}

export function linkClasses(edge) {
    return `o_workflow_canvas_link o_workflow_canvas_${edge.condition}`;
}

export function edgeLabel(edge) {
    if (edge.label) {
        return edge.label;
    }
    const delay =
        edge.delay > 0
            ? `${edge.delay} ${timeUnitLabel(edge.delay_unit) || ""}`.trim()
            : "";
    if (edge.condition === "event" && edge.event_code) {
        const event = edge.event_label || edge.event_code;
        return delay
            ? String(_t("%(event)s, then %(delay)s", { event, delay }))
            : event;
    }
    if (edge.condition === "no_event" && edge.event_code) {
        if (edge.event_label) {
            return String(
                _t("%(event)s within %(delay)s", { event: edge.event_label, delay }),
            );
        }
        return String(
            _t("no %(event)s within %(delay)s", { event: edge.event_code, delay }),
        );
    }
    if (edge.condition === "expression" && edge.condition_expr) {
        return delay
            ? String(
                  _t("%(expression)s, then %(delay)s", {
                      expression: edge.condition_expr,
                      delay,
                  }),
              )
            : edge.condition_expr;
    }
    if (["on_success", "on_error", "always"].includes(edge.condition) && delay) {
        return String(_t("after %(delay)s", { delay }));
    }
    return "";
}

export function conditionLabel(condition) {
    return {
        on_success: _t("on success"),
        on_error: _t("on error"),
        always: _t("always"),
        expression: _t("if"),
        event: _t("on event"),
        no_event: _t("without event"),
    }[condition];
}

export function timeUnitLabel(unit) {
    return {
        minute: _t("minutes"),
        hour: _t("hours"),
        day: _t("days"),
        week: _t("weeks"),
        month: _t("months"),
    }[unit];
}

export function stepDetail(step) {
    if (step.node_type === "wait") {
        return `${step.wait_delay} ${timeUnitLabel(step.wait_unit) || ""}`.trim();
    }
    if (step.node_type === "approval") {
        return step.approver_names || "";
    }
    if (step.node_type === "subflow") {
        return step.subflow_name || "";
    }
    return step.detail || "";
}

export function runtimeStateLabel(state) {
    return {
        waiting: _t("Waiting"),
        scheduled: _t("Scheduled"),
        ready: _t("Ready"),
        in_progress: _t("In progress"),
        paused: _t("Paused"),
        done: _t("Done"),
        skipped: _t("Skipped"),
        error: _t("Error"),
        cancel: _t("Cancelled"),
    }[state];
}

export function shortName(name) {
    if (!name) {
        return "";
    }
    return name.length > NAME_LIMIT ? `${name.slice(0, NAME_LIMIT - 1)}…` : name;
}

/**
 * Which conditions a reader may draw from a step's right edge.
 *
 * A rule that does not record its runs cannot honour anything but "on success"
 * — `workflow.edge._check_condition_is_honoured` refuses the rest — so those
 * ports are not offered rather than offered and rejected.
 */
export function draggableConditions(runtimeBacked) {
    return runtimeBacked ? DRAGGABLE_CONDITIONS : ["on_success"];
}

/**
 * The output ports of one step: every condition it may still be given, plus
 * every condition it already carries, so an existing edge always has a port
 * to leave from.
 */
export function outputPortsFor(nodeId, edges, runtimeBacked) {
    const draggable = draggableConditions(runtimeBacked);
    const used = new Set(
        edges.filter((edge) => edge.source === nodeId).map((edge) => edge.condition),
    );
    return CONDITIONS.filter(
        (condition) => draggable.includes(condition) || used.has(condition),
    ).map((condition) => ({
        id: condition,
        direction: "output",
        label: conditionLabel(condition),
        provides: PORT_KIND,
    }));
}

/**
 * Rank every step by its longest path from a step with no predecessor, then
 * lay the ranks out left to right.
 *
 * Sizes come from the payload, so a rank is as wide as its widest step and a
 * column is as tall as the steps stacked in it: a step somebody widened does
 * not end up overlapping its neighbour.
 *
 * `workflow.edge._check_no_cycle` makes the graph acyclic, so the ranking is
 * well defined; a payload that contradicts that still terminates, with the
 * remaining steps placed in one column rather than looping forever.
 *
 * @param {Object[]} nodes payload steps, each optionally carrying width/height
 * @param {Object[]} edges payload edges
 * @param {{ width: number, height: number }} defaultSize
 * @returns {Map<number, { x: number, y: number }>}
 */
export function layoutWorkflow(nodes, edges, defaultSize) {
    const pending = new Map(nodes.map((node) => [node.id, new Set()]));
    const successors = new Map(nodes.map((node) => [node.id, []]));
    for (const edge of edges) {
        if (!pending.has(edge.target) || !successors.has(edge.source)) {
            continue;
        }
        pending.get(edge.target).add(edge.source);
        successors.get(edge.source).push(edge.target);
    }
    const byId = new Map(nodes.map((node) => [node.id, node]));
    const positions = new Map();
    let unplaced = nodes.map((node) => node.id);
    let columnX = 0;
    while (unplaced.length) {
        let layer = unplaced.filter((id) => pending.get(id).size === 0);
        if (!layer.length) {
            layer = unplaced;
        }
        layer.sort((idA, idB) => {
            const nodeA = byId.get(idA);
            const nodeB = byId.get(idB);
            return (nodeA.sequence ?? 0) - (nodeB.sequence ?? 0) || idA - idB;
        });
        let rowY = 0;
        let columnWidth = 0;
        for (const id of layer) {
            const node = byId.get(id);
            positions.set(id, { x: columnX, y: rowY });
            rowY += (node.height || defaultSize.height) + ROW_GAP;
            columnWidth = Math.max(columnWidth, node.width || defaultSize.width);
        }
        const placed = new Set(layer);
        for (const id of layer) {
            for (const target of successors.get(id)) {
                pending.get(target).delete(id);
            }
        }
        unplaced = unplaced.filter((id) => !placed.has(id));
        columnX += columnWidth + COLUMN_GAP;
    }
    return positions;
}

/**
 * Translate `automation.rule.get_workflow_graph`'s payload into the graph the
 * flow editor draws: one node per step, one connection per edge, and the
 * edge's condition carried by the port it leaves from.
 *
 * Every figure the editor needs comes out of the payload, sizes included, so
 * the canvas restates none of the geometry the server enforces.
 */
export function toFlowGraph(payload) {
    const runtimeBacked = Boolean(payload.runtime_backed);
    const size = payload.node_size;
    const laidOut = payload.is_positioned
        ? null
        : layoutWorkflow(payload.nodes, payload.edges, size.default);
    return {
        nodes: payload.nodes.map((node) => ({
            id: node.id,
            type: node.node_type || "action",
            position: laidOut ? laidOut.get(node.id) : { x: node.pos_x, y: node.pos_y },
            size: {
                width: node.width || size.default.width,
                height: node.height || size.default.height,
            },
            headerHeight: size.header_height,
            record: {
                resModel: "ir.actions.server",
                resId: node.id,
                data: { name: node.name },
            },
            input: {
                id: INPUT_PORT_ID,
                direction: "input",
                accepts: [PORT_KIND],
            },
            outputs: outputPortsFor(node.id, payload.edges, runtimeBacked),
            data: { ...node, label: shortName(node.name) },
            deletable: node.deletable === true,
        })),
        connections: payload.edges.map((edge) => ({
            id: edge.id,
            sourceNodeId: edge.source,
            sourcePortId: edge.condition,
            targetNodeId: edge.target,
            targetPortId: INPUT_PORT_ID,
            data: edge,
        })),
    };
}
