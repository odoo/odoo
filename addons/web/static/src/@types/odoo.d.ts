interface OdooModule {
    deps: string[];
    fn: OdooModuleFactory;
    ignoreMissingDeps: boolean;
}

type OdooModuleFactory<T = string> = (require: (dependency: T) => any) => any;

type OdooModuleDefineFn = <T = string>(name: string, deps: T[], factory: OdooModuleFactory<T>, lazy?: boolean) => void;

class ModuleLoader {
    define: OdooModuleDefineFn;
    factories: Map<string, OdooModule>;
    failed: Set<string>;
    jobs: Set<string>;
    modules: Map<string, any>;
}

declare const odoo: {
    csrf_token: string;
    debug: string;
    define: OdooModuleDefineFn;
    loader: ModuleLoader;
};
