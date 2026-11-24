declare module "models" {
    export interface Attachment {
        voice: Readonly<boolean>;
        voiceMetadata: Readonly<VoiceMetadata|undefined>;
    }
    export interface Composer {
        voiceAttachment: Readonly<Attachment|undefined>;
    }
    export interface Store {
        voiceMessage: import("@mail/discuss/voice_message/common/voice_message_plugin").VoiceMessagePlugin;
    }
}
