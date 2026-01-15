import { fields } from "@mail/model/misc";
import { Record } from "@mail/model/record";

export class VoiceMetadata extends Record {
    static _name = "discuss.voice.metadata";
    static id = "id";

    attachment_id = fields.One("ir.attachment", { inverse: "voice_ids" });
}

VoiceMetadata.register();
