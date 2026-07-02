import { Component, props, types as t } from "@odoo/owl";

export class BlogNavSheet extends Component {
    static template = "website_blog.BlogNavSheet";
    props = props({ blogs: t.array(), close: t.function() });
}
