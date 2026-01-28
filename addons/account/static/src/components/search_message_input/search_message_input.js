import { MailMessageSearchModel } from "@mail/core/common/search_message_input";
import { patch } from "@web/core/utils/patch";

// TODO remove and use the field service with setTrackedModels

patch(MailMessageSearchModel.prototype, {
    async load(config) {
        if (config.searchViewFields && "tracking.account.move,date" in config.searchViewFields) {
            const searchModel = this.env.model.env.searchModel;
            const fields = await searchModel.fieldService.loadFields("account.move.line");
            Object.values(fields)
                .filter((f) => f.tracking && !f.related)
                .forEach((f) => {
                    const fname = `tracking.account.move.line,${f.name}`;
                    config.searchViewFields[fname] = {
                        ...f,
                        name: fname,
                    };
                });
        }
        return super.load(config);
    },
});
