import { fields, getKwArgs, models } from "@web/../tests/web_test_helpers";

export class MailTestRottingResource extends models.ServerModel {
    _name = "mail.test.rotting.resource";

    is_rotting = fields.Boolean({ string: "Rotting" });

    /** @override changing the stage resets the date of last stage update, hence the rotting */
    write() {
        const { ids, vals } = getKwArgs(arguments, "ids", "vals");
        return super.write(ids, "stage_id" in vals ? { ...vals, is_rotting: false } : vals);
    }
}
