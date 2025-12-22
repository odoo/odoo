import { before, withFetch } from "@odoo/hoot";
import { loadBundle } from "@web/core/assets";
import * as _fields from "./_framework/mock_server/mock_fields";
import * as _models from "./_framework/mock_server/mock_model";
import { IrAttachment } from "./_framework/mock_server/mock_models/ir_attachment";
import { IrModel } from "./_framework/mock_server/mock_models/ir_model";
import { IrModelAccess } from "./_framework/mock_server/mock_models/ir_model_access";
import { IrModelFields } from "./_framework/mock_server/mock_models/ir_model_fields";
import { IrRule } from "./_framework/mock_server/mock_models/ir_rule";
import { IrUiView } from "./_framework/mock_server/mock_models/ir_ui_view";
import { ResCompany } from "./_framework/mock_server/mock_models/res_company";
import { ResCountry } from "./_framework/mock_server/mock_models/res_country";
import { ResCurrency } from "./_framework/mock_server/mock_models/res_currency";
import { ResGroups } from "./_framework/mock_server/mock_models/res_groups";
import { ResPartner } from "./_framework/mock_server/mock_models/res_partner";
import { ResUsers } from "./_framework/mock_server/mock_models/res_users";
import { defineModels } from "./_framework/mock_server/mock_server";
import { globalCachedFetch } from "./_framework/module_set.hoot";

/**
 * @typedef {import("./_framework/dom_test_helpers").DragAndDropOptions} DragAndDropOptions
 * @typedef {import("./_framework/mock_server/mock_fields").FieldType} FieldType
 * @typedef {import("./_framework/mock_server/mock_server").MockServerEnvironment} MockServerEnvironment
 * @typedef {import("./_framework/mock_server/mock_model").ModelRecord} ModelRecord
 */

/**
 * @template T
 * @typedef {import("./_framework/mock_server/mock_server").KwArgs<T>} KwArgs
 */

/**
 * @template T
 * @typedef {import("./_framework/mock_server/mock_server").RouteCallback<T>} RouteCallback
 */

export { asyncStep, waitForSteps } from "./_framework/async_step";
export {
    findComponent,
    getDropdownMenu,
    mountWithCleanup,
} from "./_framework/component_test_helpers";
export { contains, defineStyle, editAce } from "./_framework/dom_test_helpers";
export {
    clearRegistry,
    getMockEnv,
    getService,
    makeDialogMockEnv,
    makeMockEnv,
    mockService,
    restoreRegistry,
} from "./_framework/env_test_helpers";
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
} from "./_framework/kanban_test_helpers";
export { Command, registerInlineViewArchs } from "./_framework/mock_server/mock_model";
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
} from "./_framework/mock_server/mock_server";
export {
    getKwArgs,
    makeKwArgs,
    makeServerError,
    MockServerError,
    unmakeKwArgs,
} from "./_framework/mock_server/mock_server_utils";
export { serverState } from "./_framework/mock_server_state.hoot";
export { patchWithCleanup } from "./_framework/patch_test_helpers";
export { preventResizeObserverError } from "./_framework/resize_observer_error_catcher";
export {
    deleteFavorite,
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
    saveFavorite,
    selectGroup,
    switchView,
    toggleActionMenu,
    toggleComparisonMenu,
    toggleFavoriteMenu,
    toggleFilterMenu,
    toggleGroupByMenu,
    toggleMenu,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleSaveFavorite,
    toggleSearchBarMenu,
    validateSearch,
} from "./_framework/search_test_helpers";
export { swipeLeft, swipeRight } from "./_framework/touch_helpers";
export { installLanguages, patchTranslations } from "./_framework/translation_test_helpers";
export {
    clickButton,
    clickCancel,
    clickFieldDropdown,
    clickFieldDropdownItem,
    clickModalButton,
    clickSave,
    clickViewButton,
    expectMarkup,
    fieldInput,
    hideTab,
    mountView,
    mountViewInDialog,
    parseViewProps,
    selectFieldDropdownItem,
} from "./_framework/view_test_helpers";
export { mountWebClient, useTestClientAction } from "./_framework/webclient_test_helpers";

export function defineWebModels() {
    return defineModels(webModels);
}

/**
 * @param {string} bundleName
 * @param {{ once?: boolean }} [options]
 */
export function preloadBundle(bundleName, options) {
    const once = options?.once || false;
    before(async function preloadBundle() {
        if (once) {
            odoo.loader.preventGlobalDefine = true;
        }
        await withFetch(globalCachedFetch, () => loadBundle(bundleName));
        if (once) {
            odoo.loader.preventGlobalDefine = false;
        }
    });
}

export const fields = _fields;
export const models = _models;

export const webModels = {
    IrAttachment,
    IrModel,
    IrModelAccess,
    IrModelFields,
    IrRule,
    IrUiView,
    ResCompany,
    ResCountry,
    ResCurrency,
    ResGroups,
    ResPartner,
    ResUsers,
};
