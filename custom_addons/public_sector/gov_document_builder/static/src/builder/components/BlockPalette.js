/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class BlockPalette extends Component {
    static template = "gov_document_builder.BlockPalette";

    setup() {
        this.store = useService("gov_document_builder_store");
        this.localState = useState({
            query: "",
        });
    }

    get groupedBlocks() {
        const query = this.localState.query.trim().toLowerCase();
        const groups = [];
        const indexByCategory = new Map();

        for (const block of this.store.state.blockCatalog) {
            const haystack = `${block.name || ""} ${block.description || ""}`.toLowerCase();
            if (query && !haystack.includes(query)) {
                continue;
            }

            const category = block.category || "Outros";
            if (!indexByCategory.has(category)) {
                indexByCategory.set(category, groups.length);
                groups.push({
                    name: category,
                    blocks: [],
                });
            }
            groups[indexByCategory.get(category)].blocks.push(block);
        }

        return groups;
    }

    updateQuery(ev) {
        this.localState.query = ev.target.value;
    }

    insertBlock(blockCode) {
        this.store.insertBlock(blockCode);
    }
}
