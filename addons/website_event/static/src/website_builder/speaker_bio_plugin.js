import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class SpeakerBioPlugin extends Plugin {
    static id = "speakerBio";
    resources = {
        so_content_addition_selector: [".s_speaker_bio"],
    };
}

registry.category("website-plugins").add(SpeakerBioPlugin.id, SpeakerBioPlugin);
