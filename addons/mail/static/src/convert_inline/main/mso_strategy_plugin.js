import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";

export class MsoStrategyPlugin extends Plugin {
    static id = "msoStrategy";
    static dependencies = [];

    // TODO EGGMAIL: replace background images with VML output
    // border in MSO can not be bigger than 8px
}

registry.category("mail-html-conversion-main-plugins").add(MsoStrategyPlugin.id, MsoStrategyPlugin);
