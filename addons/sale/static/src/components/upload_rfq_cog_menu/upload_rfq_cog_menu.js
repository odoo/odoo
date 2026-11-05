import { DocumentFileUploader } from '@account/components/document_file_uploader/document_file_uploader';
import { DropdownItem } from '@web/core/dropdown/dropdown_item';
import { registry } from '@web/core/registry';
import { exprToBoolean } from "@web/core/utils/strings";
import { useEnv } from '@web/owl2/utils';

const cogMenuRegistry = registry.category('cogMenu');

/**
 * 'Upload Request for Quotation' Menu
 *
 * This menu allows users to import requests for quotation.
 */
export class QuotationRequestUploader extends DocumentFileUploader {
    static template = 'upload_rfq_cog_menu.QuotationRequestUploader';
    static components = {
        ...DocumentFileUploader.components,
        DropdownItem,
    }

    getResModel() {
        return 'sale.order';
    }
}

export const quotationUploaderMenuItem = {
    Component: QuotationRequestUploader,
    groupNumber: 0,
    isDisplayed() {
        const env = useEnv();
        return (
            env.searchModel.resModel === 'sale.order'
            && ['list', 'kanban'].includes(env.config.viewType)
            && exprToBoolean(env.config.viewArch.getAttribute('create'), true)
        );
    },
};

cogMenuRegistry.add('quotation-upload-menu', quotationUploaderMenuItem);
