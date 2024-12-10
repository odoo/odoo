import { ServerModel } from "../mock_model";
import { serverState } from "../../mock_server_state.hoot";

export class ResCountry extends ServerModel {
    _name = "res.country";

    _records = serverState.countries.map((country) => ({
        id: country.id,
        name: country.name,
        code: country.code,
    }));
}
