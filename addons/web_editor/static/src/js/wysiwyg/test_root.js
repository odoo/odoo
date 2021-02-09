/** @odoo-module alias=web_editor.wysiwyg.root.test  */
import WysiwygRoot from "web_editor.wysiwyg.root";

WysiwygRoot.include({
    assetLibs: null // We need to add the asset because tests performed overwrites (Dialog, Unbreakable...)
});
