declare module "models" {
    import { VoiceMetadata as VoiceMetadataClass } from "@mail/discuss/voice_message/common/voice_metadata_model";

    export interface VoiceMetadata extends VoiceMetadataClass {}

    export interface Attachment {
        voice: Readonly<boolean>;
        voice_ids: VoiceMetadata[];
    }
    export interface Composer {
        voiceAttachment: Readonly<Attachment|undefined>;
    }
    export interface Store {
        "discuss.voice.metadata": StaticMailRecord<VoiceMetadata, typeof VoiceMetadataClass>;
    }

    export interface Models {
        "discuss.voice.metadata": VoiceMetadata;
    }
}
