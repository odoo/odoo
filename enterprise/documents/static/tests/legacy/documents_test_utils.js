/** @odoo-module **/

import { registry } from "@web/core/registry";
import { makeView } from "@web/../tests/views/helpers";
import { start } from "@mail/../tests/helpers/test_utils";

// Services
import { busParametersService } from "@bus/bus_parameters_service";
import { imStatusService } from "@bus/im_status_service";
import { multiTabService } from "@bus/multi_tab_service";
import { busService } from "@bus/services/bus_service";
import { presenceService } from "@bus/services/presence_service";
import { documentService } from "@documents/core/document_service";
import { storeService } from "@mail/core/common/store_service";
import { voiceMessageService } from "@mail/discuss/voice_message/common/voice_message_service";
import { fileUploadService } from "@web/core/file_upload/file_upload_service";

export function getEnrichedSearchArch(searchArch='<search></search>') {
    var searchPanelArch = `
        <searchpanel class="o_documents_search_panel">
            <field name="folder_id" string="Folders"/>
        </searchpanel>
    `;
    return searchArch.split('</search>')[0] + searchPanelArch + '</search>';
}

export async function createDocumentsView(params) {
    params.searchViewArch = getEnrichedSearchArch(params.searchViewArch);
    return makeView(params);
}

export async function createFolderView(params) {
    params.searchViewArch = '<search></search>';
    return makeView(params);
}

export async function createDocumentsViewWithMessaging(params) {
    const serverData = params.serverData || {};
    serverData.views = serverData.views || {};
    const searchArchs = {};
    for (const viewKey in serverData.views) {
        const [modelName] = viewKey.split(',');
        searchArchs[`${modelName},false,search`] = getEnrichedSearchArch(serverData.views[`${modelName},false,search`]);
    };
    Object.assign(serverData.views, searchArchs);
    return start(params);
}

/**
 * Load the services needed to test the documents views.
 */
export function loadServices(extraServices = {}) {
    const REQUIRED_SERVICES = {
        documents_pdf_thumbnail: {
            start() {
                return {
                    enqueueRecords: () => {},
                };
            },
        },
        "bus.parameters": busParametersService,
        "document.document": documentService,
        "discuss.voice_message": voiceMessageService,
        "mail.store": storeService,
        bus_service: busService,
        im_status: imStatusService,
        file_upload: fileUploadService,
        multi_tab: multiTabService,
        presence: presenceService,
        ...extraServices,
    };

    const serviceRegistry = registry.category("services");
    for (const [serviceName, service] of Object.entries(REQUIRED_SERVICES)) {
        if (!serviceRegistry.contains(serviceName)) {
            serviceRegistry.add(serviceName, service);
        }
    }
}
