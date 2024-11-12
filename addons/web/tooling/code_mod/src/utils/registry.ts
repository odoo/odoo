import { NodePath } from "@babel/traverse";

import { getBindingPath } from "./binding";
import { ExpressionPattern } from "./pattern";

const viewRegistryPattern1 = new ExpressionPattern("viewRegistry");
const viewRegistryPattern2 = new ExpressionPattern("registry.category('views')");

export function isViewRegistry(path: NodePath) {
    if (!path.isExpression()) {
        return false;
    }
    if (path.isIdentifier()) {
        const valuePath = getBindingPath(path)?.get("init");
        if (!valuePath || valuePath instanceof Array) {
            return false;
        }
        if (valuePath.isExpression()) {
            return Boolean(viewRegistryPattern2.detect(valuePath));
        }
        return false;
    }
    return Boolean(viewRegistryPattern1.detect(path) || viewRegistryPattern2.detect(path));
}
