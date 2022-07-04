/** @odoo-module **/

const { Component, useState } = owl;

export class WebsiteLoader extends Component {
    setup() {
        const initialState = {
            isVisible: false,
            title: '',
            showTips: false,
        };

        this.state = useState({
            ...initialState,
        });
        this.props.bus.on('SHOW-WEBSITE-LOADER', this, (props) => {
            this.state.isVisible = true;
            this.state.title = props && props.title;
            this.state.showTips = props && props.showTips;
        });
        this.props.bus.on('HIDE-WEBSITE-LOADER', this, () => {
            for (const key of Object.keys(initialState)) {
                this.state[key] = initialState[key];
            }
        });
    }
}
WebsiteLoader.template = 'website.website_loader';
