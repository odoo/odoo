import { Domain } from "@web/core/domain";
import { getKwArgs } from "@web/../tests/_framework/mock_server/mock_server_utils";

/** Mock of the python `hierarchy_read`, to be assigned on a mock model. */
export function hierarchyRead() {
    const kwargs = getKwArgs(
        arguments, "domain", "specification", "parent_field_name", "roots_only",
        "offset", "limit", "order", "count_limit"
    );
    const { domain, specification, parent_field_name: parentField, roots_only: rootsOnly } = kwargs;
    const { offset, limit, order, count_limit: countLimit } = kwargs;

    const read = (d) => this.web_search_read(d, specification, offset, limit, order, countLimit);
    const readParent = (id) => this.web_read([id], specification)[0] || false;
    const childrenOf = (id) => Domain.and([domain, [[parentField, "=", id]]]).toList();

    // simplified: does not skip conditions under "|" or "!"
    const targetId = domain.find(
        (c) => Array.isArray(c) && c[0] === parentField && c[1] === "=" && Number.isInteger(c[2]) && c[2]
    )?.[2];
    if (targetId) {
        return { parent: readParent(targetId), ...read(domain) };
    }
    if (rootsOnly) {
        const rootsDomain = Domain.and([domain, [[parentField, "=", false]]]).toList();
        const candidates = this.search(rootsDomain, 0, 2);
        if (candidates.length === 1) {
            return { parent: readParent(candidates[0]), ...read(childrenOf(candidates[0])) };
        }
        return { parent: false, ...read(rootsDomain) };
    }
    return { parent: false, ...read(domain) };
}