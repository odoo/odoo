// @ts-check
/** @odoo-module native */

import { isMobileOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/translation";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list";

import { PromoteStudioDialog } from "./promote_studio_dialog.js";

/**
 * @typedef {ListRenderer & {
 *     actionService: import("services").ServiceFactories["action"],
 *     dialogService: import("services").ServiceFactories["dialog"],
 *     studioEditable: boolean,
 * }} PromoteStudioListRenderer
 */

export const patchListRendererDesktop = () => ({
    /** @this {PromoteStudioListRenderer} */
    setup() {
        super.setup(...arguments);
        this.dialogService = useService("dialog");
        const list = this.props.list;

        const { actionId, actionType, actionXmlId } = this.env.config || {};
        const resModel = this.props.list.resModel;

        const isPotentiallyEditable =
            !isMobileOS() &&
            !this.env.inDialog &&
            user.isSystem &&
            list === list.model.root &&
            actionId &&
            actionType === "ir.actions.act_window";

        const computeStudioEditable = () => {
            if (!actionXmlId) {
                return false;
            }
            if (resModel.indexOf("settings") > -1 && resModel.indexOf("x_") !== 0) {
                return false;
            }
            if (resModel === "board.board") {
                return false;
            }
            if (resModel === "knowledge.article") {
                return false;
            }
            if (resModel === "account.bank.statement.line") {
                return false;
            }
            return Boolean(resModel);
        };

        this.studioEditable = isPotentiallyEditable && computeStudioEditable();
    },

    /**
     * @this {PromoteStudioListRenderer}
     * @returns {boolean}
     */
    isStudioEditable() {
        return this.studioEditable;
    },

    /**
     * @this {PromoteStudioListRenderer}
     * @returns {boolean}
     */
    get displayOptionalFields() {
        return this.isStudioEditable() || super.displayOptionalFields;
    },

    /**
     * @private
     * @this {PromoteStudioListRenderer}
     */
    onSelectedAddCustomField() {
        this.dialogService.add(PromoteStudioDialog, {
            title: _t("Odoo Studio - Add new fields to any view"),
        });
    },
});

patch(ListRenderer.prototype, patchListRendererDesktop());
