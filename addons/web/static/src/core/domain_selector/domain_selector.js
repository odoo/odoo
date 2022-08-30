/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { DomainSelectorRootNode } from "./domain_selector_root_node";

const { Component } = owl;

export class DomainSelector extends Component {
    setup() {
        this.nextNodeId = 0;
    }

    buildTree() {
        try {
            const domain = new Domain(this.props.value);
            const ctx = {
                parent: null,
                index: 0,
                domain: domain.toList(),
                get currentElement() {
                    return ctx.domain[ctx.index];
                },
                next() {
                    ctx.index++;
                },
                getFullDomain() {
                    return rootNode.computeDomain().toString();
                },
            };

            const rootNode = this.makeRootNode(ctx);
            ctx.parent = rootNode;
            this.traverseNode(ctx);

            return ctx.parent;
        } catch (_e) {
            // WOWL TODO: rethrow error when not the expected type
            return false;
        }
    }

    traverseNode(ctx) {
        if (ctx.index < ctx.domain.length) {
            if (typeof ctx.currentElement === "string" && ["&", "|"].includes(ctx.currentElement)) {
                this.traverseBranchNode(ctx);
            } else {
                this.traverseLeafNode(ctx);
            }
        }
    }
    traverseBranchNode(ctx) {
        if (ctx.parent.type !== "branch" || ctx.parent.operator !== ctx.currentElement) {
            const node = this.makeBranchNode(ctx, ctx.currentElement, []);
            ctx.parent.operands.push(node);
            ctx = Object.assign(Object.create(ctx), { parent: node });
        }
        ctx.next();
        this.traverseNode(ctx);
        ctx.next();
        this.traverseNode(ctx);
    }
    traverseLeafNode(ctx) {
        const condition = ctx.currentElement;
        const [leftOperand, operator, rightOperand] = condition;
        const node = this.makeLeafNode(ctx, operator, [leftOperand, rightOperand]);
        ctx.parent.operands.push(node);
    }

    makeBranchNode(ctx, operator, operands) {
        const updateDomain = () => this.props.update(ctx.getFullDomain());
        const makeFakeNode = this.makeFakeNode.bind(this);

        return {
            type: "branch",
            id: this.nextNodeId++,
            operator,
            operands,
            computeDomain() {
                return Domain.combine(
                    this.operands.map((operand) => operand.computeDomain()),
                    this.operator === "&" ? "AND" : "OR"
                );
            },
            update(operator) {
                this.operator = operator;
                updateDomain();
            },
            insert(newNodeType) {
                const newNode = makeFakeNode(ctx, newNodeType);
                const operands = ctx.parent.operands;
                operands.splice(operands.indexOf(this) + 1, 0, newNode);
                updateDomain();
            },
            delete() {
                const operands = ctx.parent.operands;
                operands.splice(operands.indexOf(this), 1);
                updateDomain();
            },
        };
    }
    makeLeafNode(ctx, operator, operands) {
        const updateDomain = () => this.props.update(ctx.getFullDomain());
        const makeFakeNode = this.makeFakeNode.bind(this);

        return {
            type: "leaf",
            id: this.nextNodeId++,
            operator,
            operands,
            computeDomain() {
                return new Domain([[this.operands[0], this.operator, this.operands[1]]]);
            },
            update(changes) {
                if ("fieldName" in changes) {
                    this.operands[0] = changes.fieldName;
                }
                if ("operator" in changes) {
                    this.operator = changes.operator;
                }
                if ("value" in changes) {
                    this.operands[1] = changes.value;
                }
                updateDomain();
            },
            insert(newNodeType) {
                const newNode = makeFakeNode(ctx, newNodeType);
                const operands = ctx.parent.operands;
                operands.splice(operands.indexOf(this) + 1, 0, newNode);
                updateDomain();
            },
            delete() {
                const operands = ctx.parent.operands;
                operands.splice(operands.indexOf(this), 1);
                updateDomain();
            },
        };
    }
    makeRootNode(ctx) {
        const updateDomain = (...args) => this.props.update(...args);
        const makeFakeNode = this.makeFakeNode.bind(this);

        return {
            type: "root",
            id: this.nextNodeId++,
            operator: "&",
            operands: [],
            computeDomain() {
                return Domain.combine(
                    this.operands.map((operand) => operand.computeDomain()),
                    "AND"
                );
            },
            update(newValue, fromDebug) {
                if (typeof newValue === "string") {
                    updateDomain(newValue, fromDebug);
                } else if (this.operands.length) {
                    this.operands[0].update(newValue);
                }
            },
            insert(newNodeType) {
                const newNode = makeFakeNode(ctx, newNodeType);
                if (ctx.parent) {
                    const operands = ctx.parent.operands;
                    operands.splice(operands.indexOf(this) + 1, 0, newNode);
                } else {
                    this.operands.push(newNode);
                }
                updateDomain(ctx.getFullDomain());
            },
            delete() {},
        };
    }

    makeFakeNode(ctx, type) {
        const [field, op, value] = this.props.defaultLeafValue;
        if (type === "branch") {
            return this.makeBranchNode(ctx, ctx.parent.operator === "&" ? "|" : "&", [
                this.makeLeafNode(ctx, op, [field, value]),
                this.makeLeafNode(ctx, op, [field, value]),
            ]);
        } else {
            return this.makeLeafNode(ctx, op, [field, value]);
        }
    }
}

Object.assign(DomainSelector, {
    template: "web._DomainSelector",
    components: {
        DomainSelectorRootNode,
    },
    props: {
        className: { type: String, optional: true },
        resModel: String,
        value: String,
        debugValue: { type: String, optional: true },
        readonly: { type: Boolean, optional: true },
        update: { type: Function, optional: true },
        isDebugMode: { type: Boolean, optional: true },
        defaultLeafValue: { type: Array, optional: true },
    },
    defaultProps: {
        readonly: true,
        update: () => {},
        isDebugMode: false,
        defaultLeafValue: ["id", "=", 1],
    },
});
