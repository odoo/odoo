import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { EDITOR_MUTATION_TYPES } from "@html_editor/core/dom_observer_plugin";

export class AuthorAvatarSyncPlugin extends Plugin {
    static id = "authorAvatarSync";
    static dependencies = ["domReferenceMap"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        /**
         * @param {import("@html_editor/core/dom_observer_plugin").SerializedMutation[]} mutations
         */
        on_pending_mutations_staged_handlers: (mutations) => {
            mutations
                .filter((m) => m.type === EDITOR_MUTATION_TYPES.ATTRIBUTES && m.attributeName === "data-oe-many2one-id")
                .map((m) => ({...m, target: this.dependencies.domReferenceMap.getNodeById(m.nodeId)}))
                .filter((m) => m.target.dataset.oeField === "author_id")
                .forEach((m) => this.authorToUpdate.set(m.target.dataset.oeId, m.value));
        },
        on_pending_mutations_normalized_handlers: () => {
            const toUpdate = this.authorToUpdate;
            this.authorToUpdate = new Map();
            for (const [oeId, id] of toUpdate.entries()) {
                for (const node of this.editable.querySelectorAll(
                    `[data-oe-model="blog.post"][data-oe-id="${oeId}"][data-oe-field="author_avatar"]`
                )) {
                    node.querySelector("img").src = `/web/image/res.partner/${id}/avatar_1024`;
                }
            }
        },
    };

    setup() {
        this.authorToUpdate = new Map();
    }
}

registry.category("website-plugins").add(AuthorAvatarSyncPlugin.id, AuthorAvatarSyncPlugin);
