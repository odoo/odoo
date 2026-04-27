import {
    addModelNamesToFetch,
    insertModelFields,
} from "@bus/../tests/helpers/model_definitions_helpers";

addModelNamesToFetch(["voip.call", "voip.provider"]);

insertModelFields("voip.call", {
    direction: { default: "outgoing" },
    state: { default: "calling" },
});
