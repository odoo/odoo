interface OdooModuleErrors {
    cycle?: string | null;
    failed?: Set<string>;
    missing?: Set<string>;
    unloaded?: Set<string>;
}

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

    constructor(root?: HTMLElement);

    addJob: (name: string) => void;

    define: (
        name: string,
        deps: string[],
        factory: OdooModuleFactoryFn,
        lazy?: boolean
    ) => OdooModule;

    findErrors: (jobs?: Iterable<string>) => OdooModuleErrors;

    findJob: () => string | null;

    reportErrors: (errors: OdooModuleErrors) => Promise<void>;

    sortFactories: () => void;

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
