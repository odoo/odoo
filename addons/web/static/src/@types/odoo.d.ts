interface OdooModuleFactory {
    deps: string[];
    fn: OdooModuleFactoryFn;
    ignoreMissingDeps: boolean;
}

class OdooModuleLoader {
    bus: EventTarget;
    checkErrorProm: Promise<void> | null;
    /**
     * Mapping [name => factory]
     */
    factories: Map<string, OdooModuleFactory>;
    /**
     * Names of failed modules
     */
    failed: Set<string>;
    /**
     * Names of modules waiting to be started
     */
    jobs: Set<string>;
    /**
     * Mapping [name => module]
     */
    modules: Map<string, OdooModule>;

    addJob: (name: string) => void;

    checkAndReportErrors: () => Promise<void>;

    define: (
        name: string,
        deps: string[],
        factory: OdooModuleFactoryFn,
        lazy?: boolean
    ) => OdooModule;

    findErrors: () => {
        failed: string[];
        cycle: string | null;
        missing: string[];
        unloaded: string[];
    };

    findJob: () => string | null;

    startModule: (name: string) => OdooModule;

    startModules: () => void;
}

type OdooModule = Record<string, any>;

type OdooModuleFactoryFn = (require: (dependency: string) => OdooModule) => OdooModule;

declare const odoo: {
    csrf_token: string;
    debug: string;
    define: OdooModuleLoader["define"];
    loader: OdooModuleLoader;
};
