import {
    Component,
    onWillStart,
    onWillUpdateProps,
    proxy,
    t,
    usePlugin,
    useProps,
    xml,
} from "@odoo/owl";
import { ORM } from "@web/core/orm_plugin";
import { HelpRenderer } from "@web/views/help/help_renderer";

/**
 * Displays a help view (see `help_id` view attribute), inlined in the view arch.
 * Loads the data of the help (see `data_method`), and gives them to the renderer.
 */
export class Help extends Component {
    static template = xml`
        <HelpRenderer archInfo="this.props.archInfo" actionHelp="this.props.actionHelp" data="this.state.data"/>`;
    static components = { HelpRenderer };
    props = useProps({
        archInfo: t.object(),
        actionHelp: t.string(),
    });

    setup() {
        this.state = proxy({ data: {} });
        if (this.props.archInfo.dataMethod) {
            this.orm = usePlugin(ORM);
            onWillStart(() => this.loadData());
            onWillUpdateProps(() => this.loadData());
        }
    }

    /**
     * Calls the `data_method` of the help with the current domain and context,
     * if they changed since the last call. The result is cached: the cached data
     * are displayed directly, and updated if the server returns other ones.
     */
    async loadData() {
        const { context, domain, resModel } = this.env.searchModel;
        const key = JSON.stringify([domain, context]);
        if (key !== this.dataKey) {
            this.dataKey = key;
            const cache = {
                type: "disk",
                update: "always",
                callback: (result, hasChanged) => {
                    if (hasChanged && key === this.dataKey) {
                        this.state.data = result;
                    }
                },
            };
            const data = await this.orm.cache(cache).call(
                resModel,
                this.props.archInfo.dataMethod,
                [domain],
                { context }
            );
            if (key === this.dataKey) {
                this.state.data = data;
            }
        }
    }
}
