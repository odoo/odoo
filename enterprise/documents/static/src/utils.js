export function getDocumentActionRequest(resId) {
    // stable-proof solution while we don't yet have document_action_preference or better
    return {
        type: "ir.actions.act_window",
        res_model: "documents.document",
        res_id: resId,
        views: [[false, "kanban"]],
        context: {
            documents_init_document_id: resId,
            documents_init_folder_id: 0,
        },
    };
}
