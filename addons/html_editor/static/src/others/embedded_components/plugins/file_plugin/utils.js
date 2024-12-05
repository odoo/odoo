import { renderToElement } from "@web/core/utils/render";

/**
 * @param {Object} attachment
 * @returns {Element}
 */
export function renderFileCard(attachment) {
    const dotSplit = attachment.name.split(".");
    const extension = dotSplit.length > 1 ? dotSplit.pop() : undefined;
    const fileData = {
        access_token: attachment.access_token,
        checksum: attachment.checksum,
        extension,
        filename: attachment.name,
        id: attachment.id,
        mimetype: attachment.mimetype,
        name: attachment.name,
        type: attachment.type,
        url: attachment.url || "",
    };
    const fileBlock = renderToElement("html_editor.EmbeddedFileBlueprint", {
        embeddedProps: JSON.stringify({ fileData }),
    });
    return fileBlock;
}
