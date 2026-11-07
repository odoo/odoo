import { patch } from "@web/core/utils/patch";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { models } from "@web/../tests/web_test_helpers";

export class PosBancontactProduct extends models.ServerModel {
    _name = "pos.bancontact.product";

    _records = [
        {
            id: 1,
            name: "Display Product",
            ppid: "display_profile_id",
            usage: "display",
        },
        {
            id: 2,
            name: "Sticker Product",
            ppid: "sticker_profile_id",
            usage: "sticker",
        },
    ];
}

patch(hootPosModels, [...hootPosModels, PosBancontactProduct]);
