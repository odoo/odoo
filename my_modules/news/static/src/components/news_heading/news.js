/* @odoo-module */

import { registry } from "@web/core/registry";
const { Component, useState, onWillStart, useRef } = owl;
import { useService } from "@web/core/utils/hooks";


export class OwlNews extends Component {
    setup(){
        this.state = useState({
        newslist:[],
        news:{news:"", imgsrc:"", description:""},
        isEdit: false,
        activeId: false,
    })

    this.orm = useService("orm")
    this.model = "owl.news"

    onWillStart(async ()=>{
        await this.getAllTask()
    })

    }

    async onRefresh(){
        a

        await this.getAllTask()
    }

    async getAllTask(){
        this.state.newslist = await this.orm.searchRead(this.model, [], ["news", "description", "imgsrc", "url"])
    }

}

OwlNews.template = 'Owl.News';

registry.category("actions").add("owl_action_news_js", OwlNews);