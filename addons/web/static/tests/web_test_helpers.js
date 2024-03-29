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
import { ResGroups } from "./_framework/mock_server/mock_models/res_groups";
import { ResPartner } from "./_framework/mock_server/mock_models/res_partner";
import { ResUsers } from "./_framework/mock_server/mock_models/res_users";
import { defineModels } from "./_framework/mock_server/mock_server";
import { translatedTerms, translationLoaded } from "@web/core/l10n/translation";

translatedTerms[translationLoaded] = true;

/**
 * @typedef {import("./_framework/mock_server/mock_fields").FieldType} FieldType
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

export {
    findComponent,
    getDropdownMenu,
    mountWithCleanup,
} from "./_framework/component_test_helpers";
export { contains, editAce } from "./_framework/dom_test_helpers";
export {
    clearRegistry,
    getService,
    makeDialogMockEnv,
    makeMockEnv,
    mockService,
} from "./_framework/env_test_helpers";
export { Command } from "./_framework/mock_server/mock_model";
export {
    MockServer,
    defineActions,
    defineMenus,
    defineModels,
    defineParams,
    getServerWebSockets,
    makeMockServer,
    onRpc,
    stepAllNetworkCalls,
} from "./_framework/mock_server/mock_server";
export { makeServerError } from "./_framework/mock_server/mock_server_utils";
export { serverState } from "./_framework/mock_server_state.hoot";
export {
    patchDate,
    patchTimeZone,
    patchTranslations,
    patchWithCleanup,
} from "./_framework/patch_test_helpers";
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
export {
    clickButton,
    clickCancel,
    clickKanbanCard,
    clickModalButton,
    clickSave,
    clickViewButton,
    expectMarkup,
    fieldInput,
    kanbanCard,
    mountView,
    mountViewInDialog,
} from "./_framework/view_test_helpers";
export { useTestClientAction } from "./_framework/webclient_test_helpers";

export function defineWebModels() {
    return defineModels(webModels);
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
    ResGroups,
    ResPartner,
    ResUsers,
};
