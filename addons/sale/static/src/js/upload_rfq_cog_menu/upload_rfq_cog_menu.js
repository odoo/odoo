import { registry } from '@web/core/registry';
import { FileUploader } from "@web/views/fields/file_handler";
import { DocumentFileUploader } from "@account/components/document_file_uploader/document_file_uploader";

const cogMenuRegistry = registry.category('cogMenu');

/**
 * 'Upload Request for Quotation' Menu
 *
 * This menu allows users to import requests for quotation.
 */
export class QuotationRequestUploader extends DocumentFileUploader {
    static template = 'upload_rfq_cog_menu.QuotationRequestUploader';
    static components = { FileUploader };
    
    getResModel() {
        return this.env.searchModel.resModel;
    }
}

export const quotationUploaderMenuItem = {
    Component: QuotationRequestUploader,
    groupNumber: 0,
    isDisplayed: ({ config, searchModel }) =>
        searchModel.resModel === 'sale.order'
        && config.viewType !== 'form',
};

cogMenuRegistry.add('quotation-upload-menu', quotationUploaderMenuItem);
