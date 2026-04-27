import { models } from "@web/../tests/web_test_helpers";

export class VoipProvider extends models.ServerModel {
    _name = "voip.provider";

    _records = [{ id: 1, name: "Default", mode: "demo" }];
}
