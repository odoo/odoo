import { Plugin, providePlugins, t, useConfig } from "@odoo/owl";
import { useMaybePlugin } from "@mail/utils/common/hooks";

const NO_ANCESTORS = Object.freeze({});

/**
 * Named ancestors of a component, e.g. whether it is in a chat window.
 *
 * Registration is explicit, as the same component may appear several times in
 * a parented chain and only it knows under which name descendants should see it.
 */
export class AncestorPlugin extends Plugin {
    ancestors = useConfig("ancestors", t.object().optional(NO_ANCESTORS));
}

/**
 * Returns the named ancestors, e.g. `useAncestors().inChatWindow`.
 *
 * @param {Record<string, any>} [registration] registers the current component
 *  under these names for itself and its subtree, e.g. `{ inChatWindow: true }`.
 *  A value can share an API, `false` hides an ancestor.
 */
export function useAncestors(registration) {
    const parentAncestors = useMaybePlugin(AncestorPlugin)?.ancestors ?? NO_ANCESTORS;
    if (!registration) {
        return parentAncestors;
    }
    const ancestors = Object.freeze({ ...parentAncestors, ...registration });
    providePlugins([AncestorPlugin], { ancestors });
    return ancestors;
}
