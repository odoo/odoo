import { describe, expect, test } from "@odoo/hoot";
import {
    canConnect,
    conditionLabel,
    edgeLabel,
    stepDetail,
    draggableConditions,
    layoutWorkflow,
    linkClasses,
    nodeClasses,
    outputPortsFor,
    runtimeStateLabel,
    shortName,
    toFlowGraph,
} from "@automation/workflow_graph";

const EDGES = [
    { id: 1, source: 10, target: 11, condition: "on_success" },
    { id: 2, source: 11, target: 12, condition: "on_error" },
];

describe("workflow canvas connection guard", () => {
    test("a fresh pair may be connected", () => {
        expect(canConnect(EDGES, 10, 12)).toBe(true);
    });

    test("a pair already connected may not be connected again", () => {
        expect(canConnect(EDGES, 10, 11)).toBe(false);
    });

    test("the reverse of an existing edge is still offered", () => {
        expect(canConnect(EDGES, 11, 10)).toBe(true);
    });

    test("a step may not be connected to itself", () => {
        expect(canConnect(EDGES, 10, 10)).toBe(false);
    });

    test("a drag that landed on nothing is refused", () => {
        expect(canConnect(EDGES, 10, undefined)).toBe(false);
        expect(canConnect(EDGES, null, 12)).toBe(false);
    });
});

describe("workflow canvas styling hooks", () => {
    test("a node with no run carries only the base class", () => {
        expect(nodeClasses({ id: 1 })).toBe("o_workflow_canvas_node");
    });

    test("a typed step is marked as one, a plain action is not", () => {
        for (const type of ["wait", "approval", "subflow"]) {
            expect(nodeClasses({ id: 1, node_type: type })).toInclude(
                `o_workflow_canvas_type_${type}`,
            );
        }
        expect(nodeClasses({ id: 1, node_type: "action" })).toBe(
            "o_workflow_canvas_node",
        );
    });

    test("a node in a run carries its state", () => {
        for (const state of [
            "waiting",
            "scheduled",
            "ready",
            "paused",
            "in_progress",
            "done",
            "skipped",
            "error",
            "cancel",
        ]) {
            expect(nodeClasses({ id: 1, runtime_state: state })).toInclude(
                `o_workflow_canvas_run_${state}`,
            );
        }
    });

    test("a link carries its condition", () => {
        for (const condition of ["on_success", "on_error", "always", "expression"]) {
            expect(linkClasses({ condition })).toInclude(
                `o_workflow_canvas_${condition}`,
            );
            expect(linkClasses({ condition })).toInclude("o_workflow_canvas_link");
        }
    });

    test("every condition has its own label", () => {
        const conditions = [
            "on_success",
            "on_error",
            "always",
            "expression",
            "event",
            "no_event",
        ];
        const labels = conditions.map((condition) => String(conditionLabel(condition)));

        for (const label of labels) {
            expect(label.length).toBeGreaterThan(0);
        }
        expect(new Set(labels).size).toBe(conditions.length);
    });

    test("a long step name is shortened, a short one is left alone", () => {
        expect(shortName("Send the email")).toBe("Send the email");
        expect(shortName("Send the email to everyone who asked").length).toBe(24);
        expect(shortName("")).toBe("");
        expect(shortName(undefined)).toBe("");
    });
});

describe("workflow canvas ports", () => {
    test("a rule that records its runs offers every drawable condition", () => {
        expect(draggableConditions(true)).toEqual(["on_success", "on_error", "always"]);
    });

    test("a rule that does not record its runs offers only on success", () => {
        expect(draggableConditions(false)).toEqual(["on_success"]);
    });

    test("a step's ports are the conditions it may be given", () => {
        const ports = outputPortsFor(10, EDGES, true);

        expect(ports.map((port) => port.id)).toEqual([
            "on_success",
            "on_error",
            "always",
        ]);
        expect(ports.every((port) => port.direction === "output")).toBe(true);
        expect(ports.every((port) => port.provides)).toBe(true);
    });

    test("a condition already carried keeps its port even when it is not drawable", () => {
        const edges = [{ id: 1, source: 10, target: 11, condition: "expression" }];

        expect(outputPortsFor(10, edges, false).map((port) => port.id)).toEqual([
            "on_success",
            "expression",
        ]);
        expect(outputPortsFor(11, edges, false).map((port) => port.id)).toEqual([
            "on_success",
        ]);
    });
});

describe("workflow canvas layout", () => {
    const SIZE = { width: 200, height: 96 };
    const NODES = [
        { id: 10, sequence: 1 },
        { id: 11, sequence: 2 },
        { id: 12, sequence: 3 },
    ];

    test("a chain is laid out left to right, one column per rank", () => {
        const positions = layoutWorkflow(NODES, EDGES, SIZE);

        expect(positions.get(10).x).toBe(0);
        expect(positions.get(11).x).toBeGreaterThan(positions.get(10).x);
        expect(positions.get(12).x).toBeGreaterThan(positions.get(11).x);
        expect(positions.get(10).y).toBe(0);
    });

    test("steps sharing a rank are stacked rather than superimposed", () => {
        const fanOut = [
            { id: 1, source: 10, target: 11, condition: "on_success" },
            { id: 2, source: 10, target: 12, condition: "on_error" },
        ];
        const positions = layoutWorkflow(NODES, fanOut, SIZE);

        expect(positions.get(11).x).toBe(positions.get(12).x);
        expect(positions.get(11).y).not.toBe(positions.get(12).y);
    });

    test("every step is placed exactly once, cycle or not", () => {
        const cyclic = [
            { id: 1, source: 10, target: 11, condition: "on_success" },
            { id: 2, source: 11, target: 10, condition: "on_success" },
        ];
        const positions = layoutWorkflow(NODES, cyclic, SIZE);

        expect(positions.size).toBe(3);
    });

    test("a widened step pushes the next column clear of itself", () => {
        const widened = [{ id: 10, sequence: 1, width: 400 }, ...NODES.slice(1)];
        const positions = layoutWorkflow(widened, EDGES, SIZE);

        expect(positions.get(11).x).toBeGreaterThanOrEqual(400);
    });

    test("a heightened step pushes the step stacked under it clear of itself", () => {
        const fanOut = [
            { id: 1, source: 10, target: 11, condition: "on_success" },
            { id: 2, source: 10, target: 12, condition: "on_error" },
        ];
        const heightened = [NODES[0], { id: 11, sequence: 2, height: 300 }, NODES[2]];
        const positions = layoutWorkflow(heightened, fanOut, SIZE);

        expect(positions.get(12).y).toBeGreaterThanOrEqual(300);
    });
});

describe("workflow canvas edge label", () => {
    test("a reader's own annotation is what the edge carries", () => {
        expect(
            edgeLabel({ condition: "on_success", label: "only for large orders" }),
        ).toBe("only for large orders");
    });

    test("an expression edge falls back to the expression it evaluates", () => {
        expect(
            edgeLabel({ condition: "expression", condition_expr: "amount > 100" }),
        ).toBe("amount > 100");
    });

    test("an annotation outranks the expression it sits beside", () => {
        expect(
            edgeLabel({
                condition: "expression",
                condition_expr: "amount > 100",
                label: "big ones only",
            }),
        ).toBe("big ones only");
    });

    test("a plain condition draws no text, because its port already says it", () => {
        for (const condition of ["on_success", "on_error", "always"]) {
            expect(edgeLabel({ condition })).toBe("");
        }
    });

    test("an expression edge missing its expression draws nothing", () => {
        expect(edgeLabel({ condition: "expression" })).toBe("");
    });

    test("an event edge names its event, and the delay after it", () => {
        expect(edgeLabel({ condition: "event", event_code: "open" })).toBe("open");
        expect(
            edgeLabel({
                condition: "event",
                event_code: "open",
                delay: 2,
                delay_unit: "day",
            }),
        ).toBe("open, then 2 days");
    });

    test("a no-event edge names the event it waits out, and for how long", () => {
        expect(
            edgeLabel({
                condition: "no_event",
                event_code: "open",
                delay: 3,
                delay_unit: "week",
            }),
        ).toBe("no open within 3 weeks");
    });

    test("an event an application named is drawn by its name", () => {
        expect(
            edgeLabel({
                condition: "event",
                event_code: "mail_open",
                event_label: "Mail: opened",
                delay: 1,
                delay_unit: "hour",
            }),
        ).toBe("Mail: opened, then 1 hours");
        expect(
            edgeLabel({
                condition: "no_event",
                event_code: "mail_open",
                event_label: "Mail: not opened",
                delay: 2,
                delay_unit: "day",
            }),
        ).toBe("Mail: not opened within 2 days");
    });

    test("a plain action shows the detail its application gives it", () => {
        expect(stepDetail({ node_type: "action", detail: "Email: Welcome" })).toBe(
            "Email: Welcome",
        );
    });

    test("a delayed plain edge says how long it waits", () => {
        expect(
            edgeLabel({ condition: "on_success", delay: 1, delay_unit: "month" }),
        ).toBe("after 1 months");
    });
});

describe("workflow canvas step detail", () => {
    test("a wait step states how long it waits", () => {
        expect(
            stepDetail({ node_type: "wait", wait_delay: 36, wait_unit: "hour" }),
        ).toBe("36 hours");
        expect(
            stepDetail({ node_type: "wait", wait_delay: 5, wait_unit: "minute" }),
        ).toBe("5 minutes");
    });

    test("an approval step names who must approve", () => {
        expect(
            stepDetail({ node_type: "approval", approver_names: "Ada, Grace" }),
        ).toBe("Ada, Grace");
    });

    test("a sub-workflow step names the automation it runs", () => {
        expect(
            stepDetail({ node_type: "subflow", subflow_name: "Nightly sweep" }),
        ).toBe("Nightly sweep");
    });

    test("a plain action step adds no second line", () => {
        expect(stepDetail({ node_type: "action", name: "x" })).toBe("");
        expect(stepDetail({ name: "x" })).toBe("");
    });

    test("a typed step with nothing to say stays empty rather than half-formed", () => {
        expect(stepDetail({ node_type: "approval" })).toBe("");
        expect(stepDetail({ node_type: "subflow" })).toBe("");
    });
});

describe("workflow canvas payload translation", () => {
    const PAYLOAD = {
        runtime_backed: true,
        is_positioned: true,
        node_size: {
            default: { width: 200, height: 96 },
            min: { width: 160, height: 72 },
            max: { width: 480, height: 320 },
            header_height: 34,
        },
        nodes: [
            {
                id: 10,
                name: "first",
                node_type: "action",
                sequence: 1,
                pos_x: 40,
                pos_y: 60,
            },
            {
                id: 11,
                name: "second",
                node_type: "wait",
                sequence: 2,
                pos_x: 300,
                pos_y: 60,
            },
        ],
        edges: [{ id: 5, source: 10, target: 11, condition: "on_error" }],
    };

    test("a placed graph keeps the coordinates the server holds", () => {
        const { nodes } = toFlowGraph(PAYLOAD);

        expect(nodes.map((node) => node.position)).toEqual([
            { x: 40, y: 60 },
            { x: 300, y: 60 },
        ]);
    });

    test("an unplaced graph is laid out instead of stacking at the origin", () => {
        const { nodes } = toFlowGraph({ ...PAYLOAD, is_positioned: false });

        expect(nodes[0].position.x).not.toBe(nodes[1].position.x);
    });

    test("an edge leaves from the port named after its condition", () => {
        const { connections } = toFlowGraph(PAYLOAD);

        expect(connections).toHaveLength(1);
        expect(connections[0].sourcePortId).toBe("on_error");
        expect(connections[0].sourceNodeId).toBe(10);
        expect(connections[0].targetNodeId).toBe(11);
    });

    test("a step points at the server action it draws", () => {
        const [node] = toFlowGraph(PAYLOAD).nodes;

        expect(node.record).toEqual({
            resModel: "ir.actions.server",
            resId: 10,
            data: { name: "first" },
        });
    });

    test("only the steps the payload marks deletable offer to be removed", () => {
        const removable = {
            ...PAYLOAD,
            nodes: [
                { ...PAYLOAD.nodes[0], deletable: true },
                { ...PAYLOAD.nodes[1], deletable: false },
            ],
        };

        const [offered, withheld] = toFlowGraph(removable).nodes;

        expect(offered.deletable).toBe(true);
        expect(withheld.deletable).toBe(false);
    });

    test("a payload that says nothing about deletion withholds it", () => {
        // A step a recorded run reached cannot be unlinked at all, so silence
        // has to read as "no": guessing yes offers a button that only ever
        // produces a foreign-key error.
        for (const node of toFlowGraph(PAYLOAD).nodes) {
            expect(node.deletable).toBe(false);
        }
    });

    test("a step carries its own size, and the default when it has none", () => {
        const sized = {
            ...PAYLOAD,
            nodes: [{ ...PAYLOAD.nodes[0], width: 320, height: 200 }, PAYLOAD.nodes[1]],
        };
        const [resized, untouched] = toFlowGraph(sized).nodes;

        expect(resized.size).toEqual({ width: 320, height: 200 });
        expect(untouched.size).toEqual(PAYLOAD.node_size.default);
        expect(resized.headerHeight).toBe(PAYLOAD.node_size.header_height);
    });

    test("every port an edge leaves from exists on its own step", () => {
        const { nodes, connections } = toFlowGraph(PAYLOAD);
        const portsPerNode = new Map(
            nodes.map((node) => [node.id, node.outputs.map((port) => port.id)]),
        );

        for (const connection of connections) {
            expect(portsPerNode.get(connection.sourceNodeId)).toInclude(
                connection.sourcePortId,
            );
        }
    });
});

describe("workflow canvas run states", () => {
    test("every run state has its own label", () => {
        const states = [
            "waiting",
            "scheduled",
            "ready",
            "in_progress",
            "paused",
            "done",
            "skipped",
            "error",
            "cancel",
        ];
        const labels = states.map((state) => String(runtimeStateLabel(state)));

        expect(new Set(labels).size).toBe(states.length);
        expect(runtimeStateLabel(undefined)).toBe(undefined);
    });
});
