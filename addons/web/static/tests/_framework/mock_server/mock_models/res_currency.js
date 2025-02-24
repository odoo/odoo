import { serverState } from "../../mock_server_state.hoot";
import { ServerModel } from "../mock_model";

export class ResCurrency extends ServerModel {
    _name = "res.currency";

    _records = Object.entries(serverState.currencies).map(
        ([id, { digits, name, position, symbol }]) => ({
            id: Number(id) + 1,
            decimal_places: digits?.at(-1) ?? 2,
            name,
            position,
            symbol,
        })
    );
}
