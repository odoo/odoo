import { patch } from "@web/core/utils/patch";
import { FormArchParser } from "@web/views/form/form_arch_parser";

patch(FormArchParser.prototype, {
    parse(xmlDoc, models, modelName) {
        const result = super.parse(...arguments);
        result.has_activities = Boolean(models[modelName].has_activities);
        return result;
    },
});
