/** @odoo-module */

import { Component, useState, onWillUpdateProps } from "@odoo/owl";

export class ChatterPager extends Component {
    setup() {
        this.state = useState({
            disabledButtons: false,
            pageCount: 1,
            pageStart: 1,
            pageEnd: 1,
            pagePrevious: 1,
            pageNext: 1,
            pages: [1],
            offset: 0,
        });
        this.computePagerState(this.props);

        onWillUpdateProps(this.onWillUpdateProps);
    }

    computePagerState(props) {
        let page = props.page || 1;
        let scope = props.pagerScope;

        const step = props.pagerStep;

        // Compute Pager
        this.state.messageCount = Math.ceil(parseFloat(props.messageCount) / step);

        page = Math.max(1, Math.min(page, this.state.messageCount));

        const pageStart = Math.max(page - parseInt(Math.floor(scope / 2)), 1);
        this.state.pageEnd = Math.min(pageStart + scope, this.state.messageCount);
        this.state.pageStart = Math.max(this.state.pageEnd - scope, 1);

        this.state.pages = Array.from(
            {length: this.state.pageEnd - this.state.pageStart + 1},
            (_, i) => i + this.state.pageStart,
        );
        this.state.pagePrevious = Math.max(this.state.pageStart, page - 1);
        this.state.pageNext = Math.min(this.state.pageEnd, page + 1);
    }

    onWillUpdateProps(nextProps) {
        this.computePagerState(nextProps);
    }

    async onPageChanged(page) {
        this.state.disabledButtons = true;
        await this.props.changePage(page);
        this.state.disabledButtons = false;
    }
}

ChatterPager.props = {
    pagerScope: Number,
    pagerStep: Number,
    page: Number,
    messageCount: Number,
    changePage: Function,
};

ChatterPager.template = 'project.ChatterPager';
