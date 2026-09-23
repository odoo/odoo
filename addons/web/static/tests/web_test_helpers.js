// @ts-check

import { after, before, withFetch } from "@odoo/hoot";
import { HomeMenuBadge } from "@web/../tests/_framework/mock_server/mock_models/home_menu_badge";
import { globalBundleCache, loadBundle } from "@web/core/assets";
import { loadChartJS } from "@web/core/lib/chartjs";
import { loadFullCalendar } from "@web/core/lib/fullcalendar";

import * as _fields from "./_framework/mock_server/mock_fields.js";
import * as _models from "./_framework/mock_server/mock_model.js";
import { IrAccess } from "./_framework/mock_server/mock_models/ir_access.js";
import { IrAttachment } from "./_framework/mock_server/mock_models/ir_attachment.js";
import { IrHttp } from "./_framework/mock_server/mock_models/ir_http.js";
import { IrModel } from "./_framework/mock_server/mock_models/ir_model.js";
import { IrModelFields } from "./_framework/mock_server/mock_models/ir_model_fields.js";
import { IrModuleCategory } from "./_framework/mock_server/mock_models/ir_module_category.js";
import { IrUiView } from "./_framework/mock_server/mock_models/ir_ui_view.js";
import { ResCompany } from "./_framework/mock_server/mock_models/res_company.js";
import { ResCountry } from "./_framework/mock_server/mock_models/res_country.js";
import { ResCurrency } from "./_framework/mock_server/mock_models/res_currency.js";
import { ResGroups } from "./_framework/mock_server/mock_models/res_groups.js";
import { ResGroupsPrivilege } from "./_framework/mock_server/mock_models/res_groups_privilege.js";
import { ResLang } from "./_framework/mock_server/mock_models/res_lang.js";
import { ResPartner } from "./_framework/mock_server/mock_models/res_partner.js";
import { ResUsers } from "./_framework/mock_server/mock_models/res_users.js";
import { ResUsersSettings } from "./_framework/mock_server/mock_models/res_users_settings.js";
import {
    defineModels,
    setDefaultMockModels,
    setDefaultMockRoute,
} from "./_framework/mock_server/mock_server.js";
import { globalCachedFetch } from "./_framework/module_set.hoot.js";

/**
 * @typedef {import("./_framework/dom_test_helpers").DragAndDropOptions} DragAndDropOptions
 * @typedef {import("./_framework/mock_server/mock_fields").FieldType} FieldType
 * @typedef {import("./_framework/mock_server/mock_server").MockServerEnvironment} MockServerEnvironment
 * @typedef {import("./_framework/mock_server/mock_model").ModelRecord} ModelRecord
 */

/**
 * @template T
 * @typedef {import("./_framework/mock_server/mock_model").KwArgs<T>} KwArgs
 */

/**
 * @typedef {import("./_framework/mock_server/mock_server").RouteCallback} RouteCallback
 */

export { asyncStep, waitForSteps } from "./_framework/async_step.js";
export {
    findComponent,
    getDropdownMenu,
    mountWithCleanup,
    waitUntilIdle,
} from "./_framework/component_test_helpers.js";
export {
    contains,
    defineStyle,
    editAce,
    sortableDrag,
} from "./_framework/dom_test_helpers.js";
export {
    clearRegistry,
    getMockEnv,
    getService,
    makeDialogMockEnv,
    makeMockEnv,
    mockService,
    registerRegistryForCleanup,
    restoreRegistry,
} from "./_framework/env_test_helpers.js";
export {
    clickKanbanLoadMore,
    clickKanbanRecord,
    createKanbanRecord,
    discardKanbanRecord,
    editKanbanColumnName,
    editKanbanRecord,
    editKanbanRecordQuickCreateInput,
    getKanbanColumn,
    getKanbanColumnDropdownMenu,
    getKanbanColumnTooltips,
    getKanbanCounters,
    getKanbanProgressBars,
    getKanbanRecord,
    getKanbanRecordTexts,
    quickCreateKanbanColumn,
    quickCreateKanbanRecord,
    toggleKanbanColumnActions,
    toggleKanbanRecordDropdown,
    validateKanbanColumn,
    validateKanbanRecord,
} from "./_framework/kanban_test_helpers.js";
export {
    Command,
    registerInlineViewArchs,
} from "./_framework/mock_server/mock_model.js";
export {
    authenticate,
    defineActions,
    defineMenus,
    defineModels,
    defineParams,
    logout,
    makeMockServer,
    MockServer,
    onRpc,
    stepAllNetworkCalls,
    withUser,
} from "./_framework/mock_server/mock_server.js";
export {
    getKwArgs,
    makeKwArgs,
    makeServerError,
    MockServerError,
    unmakeKwArgs,
} from "./_framework/mock_server/mock_server_utils.js";
export { serverState } from "./_framework/mock_server_state.hoot.js";
export {
    mockServiceWorkerContainer,
    mockServiceWorkerRegistration,
} from "./_framework/mock_service_worker.js";
export { patchWithCleanup } from "./_framework/patch_test_helpers.js";
export { preventResizeObserverError } from "./_framework/resize_observer_error_catcher.js";
export {
    editFavorite,
    editFavoriteName,
    editPager,
    editSearch,
    getButtons,
    getFacetTexts,
    getMenuItemTexts,
    getPagerLimit,
    getPagerValue,
    getVisibleButtons,
    isItemSelected,
    isOptionSelected,
    mountWithSearch,
    openAddCustomFilterDialog,
    pagerNext,
    pagerPrevious,
    removeFacet,
    saveAndEditFavorite,
    saveFavorite,
    selectGroup,
    switchView,
    toggleActionMenu,
    toggleFavoriteMenu,
    toggleFilterMenu,
    toggleGroupByMenu,
    toggleMenu,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleSaveFavorite,
    toggleSearchBarMenu,
    validateSearch,
} from "./_framework/search_test_helpers.js";
export { swipeLeft, swipeRight } from "./_framework/touch_helpers.js";
export {
    allowTranslations,
    installLanguages,
    patchTranslations,
} from "./_framework/translation_test_helpers.js";
export {
    clickButton,
    clickCancel,
    clickFieldDropdown,
    clickFieldDropdownItem,
    clickModalButton,
    clickSave,
    clickViewButton,
    editSelectMenu,
    expectMarkup,
    fieldInput,
    hideTab,
    mountView,
    mountViewInDialog,
    parseViewProps,
    selectFieldDropdownItem,
} from "./_framework/view_test_helpers.js";
export {
    mountActionHost,
    mountWebClient,
    useTestClientAction,
} from "./_framework/webclient_test_helpers.js";

export function defineWebModels() {
    return defineModels(webModels);
}

/** @param {string} bundleName */
export function preloadBundle(bundleName) {
    before(async function preloadBundle() {
        globalBundleCache.delete(bundleName);
        await withFetch(globalCachedFetch, () => loadBundle(bundleName));
    });
    after(() => {
        globalBundleCache.delete(bundleName);
    });
}

export function preloadChartJS() {
    before(async function preloadChartJS() {
        await withFetch(globalCachedFetch, () => loadChartJS());
    });
}

export function preloadFullCalendar() {
    before(async function preloadFullCalendar() {
        await withFetch(globalCachedFetch, () => loadFullCalendar());
    });
}

/**
 * @param {string} dataURI
 * @returns {Blob}
 */
export function dataURItoBlob(dataURI) {
    const binary = atob(dataURI.split(",")[1]);
    const array = [];
    const mimeString = dataURI.split(",")[0].split(":")[1].split(";")[0];
    for (let i = 0; i < binary.length; i++) {
        array.push(binary.charCodeAt(i));
    }
    return new Blob([new Uint8Array(array)], { type: mimeString });
}

export const fields = _fields;
export const models = _models;

export const webModels = {
    HomeMenuBadge,
    IrHttp,
    IrAccess,
    IrAttachment,
    IrModel,
    IrModelFields,
    IrModuleCategory,
    IrUiView,
    ResCompany,
    ResCountry,
    ResCurrency,
    ResGroupsPrivilege,
    ResGroups,
    ResLang,
    ResPartner,
    ResUsers,
    ResUsersSettings,
};

setDefaultMockModels({ IrHttp, HomeMenuBadge });

setDefaultMockRoute("/mail/data", () => ({}));
setDefaultMockRoute("/mail/action", () => ({}));
