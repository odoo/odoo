import { onRpc } from "@web/../tests/web_test_helpers";

/**
 * Mock of `hierarchy_read` (see `web_hierarchy/models/models.py`): the records matching
 * the domain are organized in trees (a record whose parent is not displayed is a root, a
 * cycle is broken on its first record), then loaded breadth-first, up to `limit`, the
 * children of each record being sorted by decreasing number of children.
 */
onRpc("hierarchy_read", function hierarchyRead({ model, args, kwargs }) {
    const [domain, specification, parentFieldName] = args;
    const { limit } = kwargs;
    const Model = this.env[model];

    const ids = Model.search(domain);
    const displayed = new Set(ids);
    const parentOf = new Map(Model.browse(ids).map((record) => [record.id, record[parentFieldName]]));

    const roots = [];
    const children = new Map(ids.map((id) => [id, []]));
    for (const id of ids) {
        const parentId = parentOf.get(id);
        if (parentId && parentId !== id && displayed.has(parentId)) {
            children.get(parentId).push(id);
        } else {
            roots.push(id);
        }
    }

    const reached = new Set();
    const visit = (rootId) => {
        reached.add(rootId);
        const stack = [rootId];
        while (stack.length) {
            const id = stack.pop();
            const kept = children.get(id).filter((childId) => !reached.has(childId));
            children.set(id, kept);
            kept.forEach((childId) => reached.add(childId));
            stack.push(...kept);
        }
    };
    roots.forEach(visit);
    for (const id of ids) {
        if (!reached.has(id)) {
            roots.push(id);
            visit(id);
        }
    }
    children.set(false, roots);

    const opened = [];
    const queue = [false];
    let remaining = limit ?? ids.length;
    for (let i = 0; i < queue.length && remaining > 0; i++) {
        const parentId = queue[i];
        const childIds = children.get(parentId);
        if (childIds.length) {
            childIds.sort((a, b) => children.get(b).length - children.get(a).length);
            const taken = childIds.slice(0, remaining);
            remaining -= taken.length;
            opened.push([parentId, taken]);
            queue.push(...taken);
        }
    }

    const selected = opened.flatMap(([, taken]) => taken);
    return {
        records: selected.length ? Model.web_read(selected, specification) : [],
        length: ids.length,
        children: opened,
    };
});
