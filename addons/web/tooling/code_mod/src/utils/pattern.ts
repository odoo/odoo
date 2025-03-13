import { parse } from "@babel/parser";
import traverse, { NodePath } from "@babel/traverse";
import * as t from "@babel/types";

// modif of isNodesEquivalent from @babel/types (added arg holes + custom part + self calls adapted)
export function areEquivalentUpToHole(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    a: any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    b: any,
    holes: Record<string, NodePath | NodePath[] | null> = {},
) {
    if (typeof a !== "object" || typeof b !== "object" || a == null || b == null) {
        return a === b;
    }

    //////////////////////////////////////////////////////////////////////////////
    // custom part
    if (t.isIdentifier(a) && a.name in holes) {
        if (holes[a.name]) {
            const equiv = areEquivalentUpToHole(holes[a.name], b);
            if (!equiv) {
                return false;
            }
        } else {
            holes[a.name] = b;
        }
        return true;
    }
    //////////////////////////////////////////////////////////////////////////////

    if (a.type !== b.type) {
        return false;
    }

    const fields = Object.keys(t.NODE_FIELDS[a.type] || a.type);
    const visitorKeys = t.VISITOR_KEYS[a.type];

    for (const field of fields) {
        const val_a = a[field];
        const val_b = b[field];
        if (typeof val_a !== typeof val_b) {
            return false;
        }
        if (val_a == null && val_b == null) {
            continue;
        } else if (val_a == null || val_b == null) {
            return false;
        }

        if (Array.isArray(val_a)) {
            if (!Array.isArray(val_b)) {
                return false;
            }
            if (val_a.length !== val_b.length) {
                return false;
            }

            for (let i = 0; i < val_a.length; i++) {
                if (!areEquivalentUpToHole(val_a[i], val_b[i], holes)) {
                    return false;
                }
            }
            continue;
        }

        if (typeof val_a === "object" && !visitorKeys?.includes(field)) {
            for (const key of Object.keys(val_a)) {
                if (val_a[key] !== val_b[key]) {
                    return false;
                }
            }
            continue;
        }

        if (!areEquivalentUpToHole(val_a, val_b, holes)) {
            return false;
        }
    }

    return true;
}

function removePrefix(location: string, prefix: string) {
    return location.slice(prefix.length);
}

function getRelativeLocation(path: NodePath, otherPath: NodePath): string {
    const prefix = `${path.getPathLocation()}.`;
    return removePrefix(otherPath.getPathLocation(), prefix).replaceAll(/\[(\d+)\]/g, ".$1");
}

class Pattern {
    _holes: Set<string>;
    _pathLocations: Record<string, string>;
    _ast: t.Node | null;
    constructor(expr: string) {
        const fileAST = parse(expr, { sourceType: "module" });
        this._holes = new Set();
        this._pathLocations = {};
        this._ast = null;
        traverse(fileAST, {
            enter: (__path) => {
                if (!this.hasTargetType(__path) || __path.parentPath === null) {
                    return;
                }
                this._ast = __path.node;
                __path.parentPath.traverse({
                    Identifier: (path) => {
                        const { name } = path.node;
                        if (/__.+/.test(name)) {
                            this._holes.add(name);
                            this._pathLocations[name] = getRelativeLocation(__path, path);
                        }
                    },
                });
                __path.stop();
            },
        });
    }
    hasTargetType(path: NodePath): boolean {
        return false;
    }
    detect(path: NodePath) {
        if (!this.hasTargetType(path)) {
            return false;
        }
        const holes: Record<string, null | NodePath | NodePath[]> = Object.fromEntries(
            [...this._holes].map((name) => [name, null]),
        );
        const equivalentUpToHoles = areEquivalentUpToHole(this._ast, path.node, holes);
        if (equivalentUpToHoles) {
            const values: Record<string, NodePath | NodePath[]> = {};
            for (const name in holes) {
                values[name] = path.get(this._pathLocations[name]);
            }
            return values;
        }
        return false;
    }
}

export class ExpressionPattern extends Pattern {
    hasTargetType(path: NodePath): boolean {
        return path.isExpression();
    }
}

export class DeclarationPattern extends Pattern {
    hasTargetType(path: NodePath) {
        return path.isVariableDeclaration();
    }
}
