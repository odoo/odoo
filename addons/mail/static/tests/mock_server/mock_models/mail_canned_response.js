import { models } from "@web/../tests/web_test_helpers";

export class MailCannedResponse extends models.ServerModel {
    _name = "mail.canned.response";

    create() {
        const cannedReponseId = super.create(...arguments);
        const [cannedResponse] = this.env["mail.canned.response"].search_read([
            ["id", "=", cannedReponseId],
        ]);
        if (cannedResponse) {
            const [partner] = this.env["res.partner"].read(this.env.user.partner_id);
            this.env["bus.bus"]._add_to_queue(
                partner,
                "mail.record/insert",
                {
                    CannedResponse: [cannedResponse],
                },
            );
        }
        return cannedReponseId;
    }

    write() {
        const res = super.write(...arguments);
        const [cannedResponse] = this.env["mail.canned.response"].search_read([
            ["id", "=", this[0].id],
        ]);
        const [partner] = this.env["res.partner"].read(this.env.user.partner_id);
        this.env["bus.bus"]._add_to_queue(partner, "mail.record/insert", {
            CannedResponse: [cannedResponse],
        });
        return res;
    }

    unlink() {
        const [partner] = this.env["res.partner"].read(this.env.user.partner_id);
        this.env["bus.bus"]._add_to_queue(partner, "mail.record/delete", {
            CannedResponse: [
                {
                    id: this[0].id,
                },
            ],
        });
        return super.unlink(...arguments);
    }
}
