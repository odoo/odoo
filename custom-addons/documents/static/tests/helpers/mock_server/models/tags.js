/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

const N_FACET_COLORS = 11

patch(MockServer.prototype, {
    /**
     * Mocks the '_get_tags' method of the model 'documents.tag'.
     */
    _mockDocumentsTag_GetTags(domain, folderId) {
        const facets = this.models['documents.facet'].records;
        const orderedTags = this.models['documents.tag'].records.sort((firstTag, secondTag) => {
            const firstTagFacet = facets.find(facet => facet.id === firstTag.facet_id);
            const secondTagFacet = facets.find(facet => facet.id === secondTag.facet_id);
            return firstTagFacet.sequence === secondTagFacet.sequence
                ? firstTag.sequence - secondTag.sequence
                : firstTagFacet.sequence - secondTagFacet.sequence;
        });
        return orderedTags.map(tag => {
            const [facet] = this.mockSearchRead('documents.facet', [[['id', '=', tag['facet_id']]]], {});
            return {
                display_name: tag.display_name,
                color_index: (facet.id % N_FACET_COLORS) + 1,
                group_id: facet.id,
                group_name: facet.name,
                group_sequence: facet.sequence,
                group_tooltip: facet.tooltip,
                id: tag.id,
                sequence: tag.sequence,
            };
        });
    },
});
