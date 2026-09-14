// @ts-check
/** @odoo-module native */

import { onWillDestroy } from "@odoo/owl";
import { makeContext } from "@web/core/context";
import { isX2Many } from "@web/core/field_types";
import { registry } from "@web/core/registry";
import { sharedComponents } from "@web/core/shared_components";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

const viewRegistry = registry.category("views");

/**
 * @param {Object} fieldNodes
 * @param {Object} fields
 * @param {Object} context
 * @param {string} resModel
 * @param {Object} viewService
 * @param {boolean} isSmall
 */
export async function loadSubViews(
    fieldNodes,
    fields,
    context,
    resModel,
    viewService,
    isSmall,
) {
    const fieldInfosToLoad = [];
    for (const fieldInfo of Object.values(fieldNodes)) {
        const fieldName = fieldInfo.name;
        const field = fields[fieldName];
        if (!isX2Many(field)) {
            continue;
        }
        if (fieldInfo.invisible === "True" || fieldInfo.invisible === "1") {
            continue;
        }
        if (!fieldInfo.field.useSubView) {
            continue;
        }

        fieldInfo.views = fieldInfo.views || {};
        let viewType = fieldInfo.viewMode || "list,kanban";
        if (viewType.includes(",")) {
            viewType = isSmall ? "kanban" : "list";
        }
        fieldInfo.viewMode = viewType;
        if (fieldInfo.views[viewType]) {
            continue;
        }
        fieldInfosToLoad.push(fieldInfo);
    }

    await Promise.all(
        fieldInfosToLoad.map(async (fieldInfo) => {
            const field = fields[fieldInfo.name];
            const viewType = fieldInfo.viewMode;

            const fieldContext = {};
            const regex = /['"](\w+_view_ref)['"] *: *['"](.*?)['"]/g;
            let matches;
            while ((matches = regex.exec(fieldInfo.context)) !== null) {
                fieldContext[matches[1]] = matches[2];
            }
            const refinedContext = {};
            for (const key of Object.keys(context)) {
                if (!key.includes("_view_ref")) {
                    refinedContext[key] = context[key];
                }
            }

            const comodel = field.relation;
            const {
                fields: comodelFields,
                relatedModels,
                views,
            } = await viewService.loadViews({
                resModel: comodel,
                views: [[false, viewType]],
                context: makeContext([fieldContext, user.context, refinedContext]),
            });
            const { ArchParser } = viewRegistry.get(viewType);
            const archInfo = new ArchParser().parse(
                views[viewType].ir,
                relatedModels,
                comodel,
            );
            fieldInfo.views[viewType] = {
                ...archInfo,
                limit: archInfo.limit || 40,
                fields: comodelFields,
            };
            fieldInfo.relatedFields = comodelFields;
        }),
    );
}

export function useFormViewInDialog() {
    const formDialogStack = useService("form_dialog_stack");
    formDialogStack.push();
    onWillDestroy(() => formDialogStack.pop());
}

sharedComponents.add("loadSubViews", loadSubViews);
sharedComponents.add("useFormViewInDialog", useFormViewInDialog);
