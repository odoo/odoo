/* @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { FileViewer as WebFileViewer } from "@web/core/file_viewer/file_viewer";
import { onWillUpdateProps } from "@odoo/owl";

export class FileViewer extends WebFileViewer {
    static template = "documents.FileViewer";
    setup() {
        super.setup();
        /** @type {import("@documents/core/document_service").DocumentService} */
        this.documentService = useService("document.document");
        this.onSelectDocument = this.documentService.documentList?.onSelectDocument;
        onWillUpdateProps((nextProps) => {
            const indexOfFileToPreview = nextProps.startIndex;
            if (
                indexOfFileToPreview !== this.state.index &&
                indexOfFileToPreview !== this.props.startIndex
            ) {
                this.activateFile(indexOfFileToPreview);
            }
            this.documentService.setPreviewedDocument(
                this.documentService.documentList.documents[nextProps.startIndex]
            );
        });
    }
    get currentFolderId() {
        return this.env.searchModel.getSelectedFolderId();
    }
    get hasSplitPdf() {
        if (!this.documentService.userIsInternal) {
            return false;
        }
        if (this.documentService.documentList?.initialRecordSelectionLength === 1) {
            return this.documentService.documentList.selectedDocument.attachment.isPdf &&
                this.documentService.documentList.selectedDocument?.record?.data?.user_permission === 'edit';
        }
        return this.documentService.documentList?.documents.every(
            (document) => document.attachment.isPdf && document.record?.data?.user_permission === 'edit'
        );
    }
    get withDownload() {
        if (this.documentService.documentList?.initialRecordSelectionLength === 1) {
            return this.documentService.documentList.selectedDocument.attachment.isUrlYoutube;
        }
        return this.documentService.documentList?.documents.every(
            (document) => document.attachment.isUrlYoutube
        );
    }
    onClickPdfSplit() {
        this.close();
        if (this.documentService.documentList?.initialRecordSelectionLength === 1) {
            return this.documentService.documentList?.pdfManagerOpenCallback([
                this.documentService.documentList.selectedDocument.record,
            ]);
        }
        return this.documentService.documentList?.pdfManagerOpenCallback(
            this.documentService.documentList.documents.map((document) => document.record)
        );
    }
    close() {
        this.documentService.documentList?.onDeleteCallback();
        this.documentService.setPreviewedDocument(null);
        super.close();
    }
    next() {
        super.next();
        this.documentService.setPreviewedDocument(
            this.documentService.documentList.documents[this.state.index]
        );

        if (this.onSelectDocument) {
            const documentList = this.documentService.documentList;
            if (
                !documentList ||
                !documentList.selectedDocument ||
                !documentList.documents ||
                !documentList.documents.length
            ) {
                return;
            }
            const index = documentList.documents.findIndex(
                (document) => document === documentList.selectedDocument
            );
            const nextIndex = index === documentList.documents.length - 1 ? 0 : index + 1;
            documentList.selectedDocument = documentList.documents[nextIndex];
            this.onSelectDocument(documentList.selectedDocument.record);
        }
    }
    previous() {
        super.previous();
        this.documentService.setPreviewedDocument(
            this.documentService.documentList.documents[this.state.index]
        );

        if (this.onSelectDocument) {
            const documentList = this.documentService.documentList;
            if (
                !documentList ||
                !documentList.selectedDocument ||
                !documentList.documents ||
                !documentList.documents.length
            ) {
                return;
            }
            const index = documentList.documents.findIndex(
                (doc) => doc === documentList.selectedDocument
            );
            // if we're on the first document, go "back" to the last one
            const previousIndex = index === 0 ? documentList.documents.length - 1 : index - 1;
            documentList.selectedDocument = documentList.documents[previousIndex];
            this.onSelectDocument(documentList.selectedDocument.record);
        }
    }
}
