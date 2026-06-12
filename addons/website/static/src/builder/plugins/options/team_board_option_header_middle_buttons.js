import { Component, xml } from "@odoo/owl";

export class TeamBoardOptionHeaderMiddleButtons extends Component {
    static template = xml`<button class="o-hb-btn fa fa-fw fa-plus btn btn-accent-color-hover" title.translate="Add a new team board" aria-label="Add a new team board" t-on-click="this.props.createNewTeamBoard"/>`;
    static props = {
        createNewTeamBoard: {
            type: Function,
        },
    };
}
