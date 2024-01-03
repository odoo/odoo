/** @odoo-module */

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

export { findComponent, mountWithCleanup } from "./_framework/component_test_helpers";
export { contains } from "./_framework/dom_test_helpers";
export { getService, makeMockEnv, mockService } from "./_framework/env_test_helpers";
export { Command } from "./_framework/mock_server/mock_model";
export {
    MockServer,
    callWorkerBundle,
    defineModels,
    getServerWebSockets,
    getServerWorkers,
    makeMockServer,
    onRpc,
} from "./_framework/mock_server/mock_server";
export { mockSession } from "./_framework/mock_session.hoot";
export { patchWithCleanup } from "./_framework/patch_test_helpers";
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
    fieldInput,
    kanbanCard,
    mountView,
    mountViewInDialog,
} from "./_framework/view_test_helpers";

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
