/** @odoo-module */

import { renderToElement } from "@web/core/utils/render";
import { TABS, MediaDialog } from '@web_editor/components/media_dialog/media_dialog';
import { encodeDataBehaviorProps } from "@knowledge/js/knowledge_utils";

/**
 * KnowledgeMediaDialog will allow to select documents and images altogether
 * for the /file command.
 */
export class KnowledgeMediaDialog extends MediaDialog {
    /**
     * @override
     */
    addTabs() {
        super.addTabs(...arguments);
        this.addTab(TABS.KNOWLEDGE_DOCUMENTS);
    }
    /**
     * @override
     * Render the selected media. This needs a custom implementation because
     * the media is rendered as a Behavior blueprint for Knowledge, hence
     * no super call.
     *
     * @param {Object} selectedMedia First element of the selectedMediaArray,
     *                 which has length = 1 in this case because this component
     *                 is meant to be used with the prop `multiSelect = false`
     * @returns {Array<HTMLElement>}
     */
    async renderMedia([selectedMedia]) {
        let accessToken = selectedMedia.access_token;
        if (!selectedMedia.public || !accessToken) {
            // Generate an access token so that anyone with read access to the
            // article can view its files.
            [accessToken] = await this.orm.call(
                'ir.attachment',
                'generate_access_token',
                [selectedMedia.id],
            )
        }
        const dotSplit = selectedMedia.name.split('.');
        const extension = dotSplit.length > 1 ? dotSplit.pop() : undefined;
        const fileData = {
            accessToken,
            checksum: selectedMedia.checksum,
            extension,
            filename: selectedMedia.name,
            id: selectedMedia.id,
            mimetype: selectedMedia.mimetype,
            name: selectedMedia.name,
            type: selectedMedia.type,
            url: selectedMedia.url,
        };
        const fileBlock = renderToElement('knowledge.FileBehaviorBlueprint', {
            behaviorProps: encodeDataBehaviorProps({
                fileData
            }),
        });
        return [fileBlock];
    }
}
