import { DocumentSelector } from "@html_editor/main/media/media_dialog/document_selector";
import { renderFileCard } from "./utils";

/**
 * Override the @see DocumentSelector to render the uploaded file as a card
 * (embedded component) with editable file name.
 */
export class FileDocumentsSelector extends DocumentSelector {
    static mediaSpecificClasses = [];

    /** @override */
    static async createElements(selectedMedia, { orm }) {
        return Promise.all(
            selectedMedia.map(async (attachment) => {
                if (!(attachment.public || attachment.access_token)) {
                    // Generate an access token so that anyone with read access to the
                    // article can view its files.
                    const [accessToken] = await orm.call("ir.attachment", "generate_access_token", [
                        attachment.id,
                    ]);
                    attachment.access_token = accessToken;
                }
                return renderFileCard(attachment);
            })
        );
    }
}
