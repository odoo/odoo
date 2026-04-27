import { getKwArgs, makeKwArgs, models } from "@web/../tests/web_test_helpers";
import { serializeDate, today } from "@web/core/l10n/dates";

export class VoipCall extends models.ServerModel {
    _name = "voip.call";

    /** @param {number[]} ids */
    abort_call(ids) {
        this.write(ids, { state: "aborted" });
        return this._format_calls(ids);
    }

    /**
     * @param {number} res_id
     * @param {string} res_model
     */
    create_and_format(res_id, res_model, ...kwargs) {
        kwargs = getKwArgs(arguments, "res_id", "res_model");
        const context = kwargs.context;
        delete kwargs.res_id;
        delete kwargs.res_model;
        delete kwargs.context;
        return this._format_calls(this.create(kwargs, makeKwArgs({ context })));
    }

    compute_display_name(calls) {
        /** @type {import("./res_partner").ResPartner} */
        const ResPartner = this.env["res.partner"];
        const getName = (call) => {
            if (call.activity_name) {
                return call.activity_name;
            }
            const preposition = call.direction === "incoming" ? "from" : "to";
            switch (call.state) {
                case "aborted":
                    return `Aborted call to ${call.phone_number}`;
                case "missed":
                    return `Missed call from ${call.phone_number}`;
                case "rejected":
                    return `Rejected call ${preposition} ${call.phone_number}`;
                default:
                    if (call.partner_id) {
                        const [partner] = ResPartner.search_read([["id", "=", call.partner_id]]);
                        return `Call ${preposition} ${partner.name}`;
                    }
                    return `Call ${preposition} ${call.phone_number}`;
            }
        };
        for (const call of calls) {
            call.display_name = getName(call);
        }
    }

    /**
     * @param {number[]} ids
     * @param {string} [activity_name]
     */
    end_call(ids, activity_name) {
        const kwargs = getKwArgs(arguments, "ids", "activity_name");
        ids = kwargs.ids;
        activity_name = kwargs.activity_name;
        this.write(ids, {
            end_date: serializeDate(today()),
            state: "terminated",
        });
        if (activity_name) {
            this.write(ids, { activity_name });
        }
        return this._format_calls(ids);
    }

    /** @param {number[]} ids */
    _format_calls(ids) {
        /** @type {import("./res_partner").ResPartner} */
        const ResPartner = this.env["res.partner"];
        if (!Array.isArray(ids)) {
            ids = [ids];
        }
        const records = this.browse(ids);
        this.compute_display_name(records);
        const formattedCalls = [];
        for (const call of records) {
            const data = {
                id: call.id,
                creationDate: call.create_date,
                direction: call.direction,
                displayName: call.display_name,
                endDate: call.end_date,
                phoneNumber: call.phone_number,
                startDate: call.start_date,
                state: call.state,
            };
            if (Number.isInteger(call.partner_id)) {
                data.partner = ResPartner._format_contacts([call.partner_id])[0];
            }
            formattedCalls.push(data);
        }
        return formattedCalls;
    }

    /** @param {number[]} ids */
    get_contact_info(ids) {
        /** @type {import("./res_partner").ResPartner} */
        const ResPartner = this.env["res.partner"];
        if (!Array.isArray(ids)) {
            ids = [ids];
        }
        const records = this.browse(ids);
        if (records.length !== 1) {
            throw new Error("self.ensure_one");
        }
        const [call] = records;
        const [partnerId] = ResPartner.search(
            ["|", ["phone", "=", call.phone_number], ["mobile", "=", call.phone_number]],
            makeKwArgs({ limit: 1 })
        );
        if (!partnerId) {
            return false;
        }
        this.write(ids, { partner_id: partnerId });
        return ResPartner._format_contacts([partnerId])[0];
    }

    _get_number_of_missed_calls() {
        const domain = [
            ["user_id", "=", this.env.uid],
            ["state", "=", "missed"],
        ];
        if (this.env.user.last_seen_phone_call) {
            domain.push([("id", ">", this.env.user.last_seen_phone_call)]);
        }
        return this.search_count(domain);
    }

    /**
     * @param {string[]} [search_terms]
     * @param {number} [offset]
     * @param {number} [limit]
     */
    get_recent_phone_calls(search_terms, offset = 0, limit) {
        const kwargs = getKwArgs(arguments, "search_terms", "offset", "limit");
        search_terms = kwargs.search_terms;
        offset = kwargs.offset || 0;
        limit = kwargs.limit;
        const domain = [["user_id", "=", this.env.uid]];
        if (search_terms) {
            for (const field of ["phone_number", "partner_id.name", "activity_name"]) {
                domain.push("|", [field, "ilike", search_terms]);
            }
        }
        const recordIds = this.search(domain, {
            offset,
            limit,
            order: "create_date DESC",
        });
        return this._format_calls(recordIds);
    }

    /** @param {number[]} ids */
    start_call(ids) {
        this.write(ids, {
            start_date: serializeDate(today()),
            state: "ongoing",
        });
        return this._format_calls(ids);
    }
}
