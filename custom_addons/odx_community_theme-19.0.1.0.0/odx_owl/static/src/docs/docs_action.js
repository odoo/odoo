/** @odoo-module **/

import { registry } from "@web/core/registry";
import { OdxOwlDocsApp } from "@odx_owl/docs/docs_app";

registry.category("actions").add("odx_owl.docs", OdxOwlDocsApp);
