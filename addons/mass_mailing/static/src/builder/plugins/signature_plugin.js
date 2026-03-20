import { registry } from "@web/core/registry";
import { SignaturePlugin } from "@html_editor/main/media/signature_plugin";

registry.category("mass_mailing-plugins").add(SignaturePlugin.id, SignaturePlugin);
