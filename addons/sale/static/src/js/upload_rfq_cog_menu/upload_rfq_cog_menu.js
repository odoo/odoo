import { registry } from '@web/core/registry';
import { exprToBoolean } from "@web/core/utils/strings";
import { DocumentFileUploader } from '@account/components/document_file_uploader/document_file_uploader';

const cogMenuRegistry = registry.category('cogMenu');

/**
 * 'Upload Request for Quotation' Menu
 *
 * This menu allows users to import requests for quotation.
 */
export class QuotationRequestUploader extends DocumentFileUploader {
    static template = 'upload_rfq_cog_menu.QuotationRequestUploader';

    getResModel() {
        return 'sale.order';
    }
}

export const quotationUploaderMenuItem = {
    Component: QuotationRequestUploader,
    groupNumber: 0,
    isDisplayed: ({ config, searchModel }) =>
        searchModel.resModel === 'sale.order'
        && ['list', 'kanban'].includes(config.viewType)
        && exprToBoolean(config.viewArch.getAttribute('create'), true),
};

cogMenuRegistry.add('quotation-upload-menu', quotationUploaderMenuItem);
