import { reactive } from "@odoo/owl";

import { Project } from "@t9n/core/project_model";

import { registry } from "@web/core/registry";

export class Store {
    constructor(env, { orm }) {
        this.env = env;
        this.orm = orm;
        this.projects = [];
        return reactive(this);
    }

    async fetchProjects() {
        const projects = await this.orm.call("t9n.project", "get_projects");
        this.projects = projects.map((p) => {
            return new Project(p.id, p.name, p.src_lang.name, p.target_langs, p.resources.length);
        });
    }
}

export const storeService = {
    dependencies: ["orm"],
    start(env, deps) {
        return new Store(env, deps);
    },
};

registry.category("services").add("t9n.store", storeService);
