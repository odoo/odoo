// @ts-check
/** @odoo-module native */
import { patch } from "@web/core/utils/patch";
import { FormArchParser } from "@web/views/form";
patch(FormArchParser.prototype, {
    /**
     * @param {Element} xmlDoc
     * @param {Object<string, Object>} models
     * @param {string} modelName
     * @returns {Object}
     */
    parse(xmlDoc, models, modelName) {
        const result = super.parse(...arguments);
        result.has_activities = Boolean(models[modelName].has_activities);
        // A model that is a member of a table-inheritance tree threads on its root.
        result.thread_model = models[modelName].thread_model || modelName;
        return result;
    },
});
