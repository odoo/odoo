import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("CustomerPopupTour: partner list searches loaded customers with SQL-like wildcard", async () => {
    const store = await setupPosEnv();
    const partnerToSearch = store.models["res.partner"].create({
        id: 9001,
        name: "Z partner to search",
        address: "",
    });
    const partnerToScroll = store.models["res.partner"].create({
        id: 9002,
        name: "Z partner to scroll",
        address: "",
    });

    const partnerList = await mountWithCleanup(PartnerList, {
        props: {
            partner: null,
            getPayload: () => {},
            close: () => {},
        },
    });

    partnerList.state.query = "Z partner to search";
    expect(partnerList.getPartners(partnerList.state.initialPartners)).toEqual([partnerToSearch]);

    partnerList.state.query = "Z partner to scroll";
    expect(partnerList.getPartners(partnerList.state.initialPartners)).toEqual([partnerToScroll]);

    partnerList.state.query = "Z%partner%search";
    expect(partnerList.getPartners(partnerList.state.initialPartners)).toEqual([partnerToSearch]);
});
