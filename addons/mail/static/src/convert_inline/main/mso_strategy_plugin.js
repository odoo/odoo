import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";

export class MsoStrategyPlugin extends Plugin {
    static id = "msoStrategy";
    static dependencies = [];

    // TODO EGGMAIL: replace background images with VML output
    // handle image borders (as they are now allowed (radius for normal images and width for icons))
    // TODO LIST:
    // div border
    // border-radius not supported for MSO
    // border <= 8px for MSO
    // background-image
    // hybrid-fluid strategy => inline-block => wrapped in table for MSO
    // buttons
    // badges (all native inline-block elements)
}

registry.category("mail-html-conversion-main-plugins").add(MsoStrategyPlugin.id, MsoStrategyPlugin);
