import { Component } from "@odoo/owl";

export class BlogNavSheet extends Component {
    static template = "website_blog.BlogNavSheet";

    static props = {
        blogs: Array,
        close: Function,
    };
}
