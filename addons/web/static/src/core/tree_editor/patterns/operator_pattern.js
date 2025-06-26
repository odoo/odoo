import { omit } from "@web/core/utils/objects";
import { Expression, isTree } from "../condition_tree";
import { constructTreeFromDomain } from "../construct_tree_from_domain";
import { Just, Nothing } from "../maybe_monad";
import { Pattern } from "./pattern";
import { TreePattern } from "./tree_pattern";

export class OperatorPattern extends Pattern {
    static of(operator, domain) {
        return new OperatorPattern(operator, domain);
    }
    constructor(operator, domain) {
        super();
        this.vars = new Set();
        this.pushVariables(constructTreeFromDomain(domain));
        this.operator = operator;
        this.treePattern = TreePattern.of(domain, this.vars);
    }
    detect(tree) {
        const mv = this.treePattern.detect(tree);
        if (mv instanceof Nothing) {
            return mv;
        }
        return Just.of({ ...mv.value, operator: this.operator });
    }
    make(values) {
        if (values.operator !== this.operator) {
            return Nothing.of();
        }
        return this.treePattern.make(omit(values, "operator"));
    }
    pushIfVar(v) {
        if (v instanceof Expression && v._ast.type === 5) {
            this.vars.add(v._ast.value);
        }
    }
    pushVariables(tree) {
        if (tree.type === "connector") {
            for (const child of tree.children) {
                this.pushVariables(child);
            }
            return;
        }
        this.pushIfVar(tree.path);
        this.pushIfVar(tree.operator);
        if (isTree(tree.value)) {
            this.pushVariables(tree.value);
        } else {
            this.pushIfVar(tree.value);
        }
    }
}
