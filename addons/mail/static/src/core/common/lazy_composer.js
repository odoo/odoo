import { Component, useProps, xml } from "@odoo/owl";
import { LazyComponent } from "@web/core/lazy_component";

/**
 * Renders the composer, loading the editor first if it is not there yet. Bundles
 * that only show the messages (portal chatter, livechat) then don't need the
 * editor: the composer and its dependent modules wait for it to be loaded.
 */
export class LazyComposer extends Component {
    static template = xml`<LazyComponent Component="'mail.Composer'" bundle="'html_editor.assets_editor_frontend'" props="this.props"/>`;
    static components = { LazyComponent };
    props = useProps();
}
