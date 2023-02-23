/** @odoo-module **/

import { Domain } from "@web/core/domain";

class DomainNode {
    static nextId = 0;

    constructor(type) {
        this.id = ++DomainNode.nextId;
        this.type = type;
    }

    toDomain() {
        return new Domain();
    }
}

// ----------------------------------------------------------------------------

export class BranchDomainNode extends DomainNode {
    constructor(operator, children = []) {
        super("branch");
        this.operator = operator;
        this.children = children;
    }

    toDomain() {
        return Domain.combine(
            this.children.map((c) => c.toDomain()),
            this.operator
        );
    }

    add(node) {
        this.children.push(node);
    }

    insertAfter(id, node) {
        const childIndex = this.children.findIndex((c) => c.id === id);
        this.children.splice(childIndex + 1, 0, node);
    }

    delete(id) {
        const childIndex = this.children.findIndex((c) => c.id === id);
        this.children.splice(childIndex, 1);
    }
}

// ----------------------------------------------------------------------------

export class LeafDomainNode extends DomainNode {
    constructor(field, operator, value) {
        super("leaf");
        this.field = field;
        this.operator = operator;
        this.value = value;
    }

    toDomain() {
        return new Domain([[this.field.name, this.operator.symbol, this.value]]);
    }

    clone() {
        return new LeafDomainNode(this.field, this.operator, this.value);
    }
}
