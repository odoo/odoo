import { models } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

patch(models.ServerModel.prototype, {
    /**
     * @override
     * @type {typeof models.Model["prototype"]["write"]}
     */
    write() {
        /** @type {import("mock_models").MailThread} */
        const MailThread = this.env["mail.thread"];

        const initialTrackedFieldValuesByRecordId = MailThread._track_prepare.call(this);
        const result = super.write(...arguments);
        if (initialTrackedFieldValuesByRecordId) {
            MailThread._track_finalize.call(this, initialTrackedFieldValuesByRecordId);
        }
        return result;
    },
});
