import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";
import { DynamicList } from "@web/model/relational_model/dynamic_list";

patch(DynamicList.prototype, {
    setup() {
        super.setup(...arguments);
        this.evalContext = { ...this.evalContext, country_code: user.activeCompany?.country_code };
    },
});
