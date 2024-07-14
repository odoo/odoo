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
        });
    }
    get hasSplitPdf() {
        if (this.documentService.documentList?.initialRecordSelectionLength === 1) {
            return this.documentService.documentList.selectedDocument.attachment.isPdf;
        }
        return this.documentService.documentList?.documents.every(
            (document) => document.attachment.isPdf
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
        super.close();
    }
    next() {
        super.next();
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
