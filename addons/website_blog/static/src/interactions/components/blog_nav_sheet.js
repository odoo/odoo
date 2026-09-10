import { Component, useProps, types as t } from "@odoo/owl";

export class BlogNavSheet extends Component {
    static template = "website_blog.BlogNavSheet";
    props = useProps({ blogs: t.array() });
}
