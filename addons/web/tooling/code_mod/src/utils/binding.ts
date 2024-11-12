import { Binding, NodePath } from "@babel/traverse";
import { Identifier } from "@babel/types";

export function getBinding(id: NodePath<Identifier>): Binding | null {
    return id.scope.getBinding(id.node.name) || null;
}

export function getBindingPath(id: NodePath<Identifier>): NodePath | null {
    const binding = getBinding(id);
    if (!binding) {
        return null;
    }
    return binding.path;
}
