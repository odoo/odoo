// @ts-check

/** @module @web/views/form/form_utils - Utility functions for form views (sub-view loading, discard hooks, toolbar setup) */

/**
 * Extracted utility functions for form views.
 *
 * These are standalone functions (not class methods) that were co-located
 * in form_controller.js. Moved here to reduce file complexity while
 * preserving the original public API via re-exports.
 */

import { onMounted, onWillUnmount, useComponent } from "@odoo/owl";
import { makeContext } from "@web/core/context";
import { registry } from "@web/core/registry";
import { parseXML } from "@web/core/utils/dom/xml";
import { user } from "@web/services/user";
import { isX2Many } from "@web/views/view_utils";

const viewRegistry = registry.category("views");

/**
 * Load sub-views for x2many fields that need them.
 *
 * Iterates over field nodes, identifies visible x2many fields whose
 * component requires a sub-view, and fetches the appropriate list or
 * kanban view definition from the server.
 *
 * @param {Object} fieldNodes - field node descriptors from the arch
 * @param {Object} fields - field definitions
 * @param {Object} context - current action context
 * @param {string} resModel - the parent model name
 * @param {Object} viewService - the view service instance
 * @param {boolean} isSmall - whether the screen is small (selects kanban over list)
 */
export async function loadSubViews(
    fieldNodes,
    fields,
    context,
    resModel,
    viewService,
    isSmall,
) {
    for (const fieldInfo of Object.values(fieldNodes)) {
        const fieldName = fieldInfo.name;
        const field = fields[fieldName];
        if (!isX2Many(field)) {
            continue; // what follows only concerns x2many fields
        }
        if (fieldInfo.invisible === "True" || fieldInfo.invisible === "1") {
            continue; // no need to fetch the sub view if the field is always invisible
        }
        if (!fieldInfo.field.useSubView) {
            continue; // the FieldComponent used to render the field doesn't need a sub view
        }

        fieldInfo.views = fieldInfo.views || {};
        let viewType = fieldInfo.viewMode || "list,kanban";
        if (viewType.includes(",")) {
            viewType = isSmall ? "kanban" : "list";
        }
        fieldInfo.viewMode = viewType;
        if (fieldInfo.views[viewType]) {
            continue; // the sub view is inline in the main form view
        }

        // extract *_view_ref keys from field context, to fetch the adequate view
        const fieldContext = {};
        const regex = /'([a-z]*_view_ref)' *: *'(.*?)'/g;
        let matches;
        while ((matches = regex.exec(fieldInfo.context)) !== null) {
            fieldContext[matches[1]] = matches[2];
        }
        // filter out *_view_ref keys from general context
        const refinedContext = {};
        for (const key in context) {
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
        const xmlDoc = parseXML(views[viewType].arch);
        const archInfo = new ArchParser().parse(xmlDoc, relatedModels, comodel);
        fieldInfo.views[viewType] = {
            ...archInfo,
            limit: archInfo.limit || 40,
            fields: comodelFields,
        };
        fieldInfo.relatedFields = comodelFields;
    }
}

/**
 * Hook to register/unregister a form-in-dialog with the parent FormController.
 *
 * Triggers bus events on mount/unmount so the parent can track nested
 * form dialogs (used to suppress auto-save when a sub-form is open).
 */
export function useFormViewInDialog() {
    const component = useComponent();
    onMounted(() => {
        component.env.bus.trigger("FORM-CONTROLLER:FORM-IN-DIALOG:ADD");
    });

    onWillUnmount(() => {
        component.env.bus.trigger("FORM-CONTROLLER:FORM-IN-DIALOG:REMOVE");
    });
}

// Register shared utilities for lower layers via registry indirection
const sharedComponents = registry.category("shared_components");
sharedComponents.add("loadSubViews", loadSubViews);
sharedComponents.add("useFormViewInDialog", useFormViewInDialog);
