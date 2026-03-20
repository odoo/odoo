// this is technically wrong, but in practice, it is correct.

interface Element {
    querySelector<E extends HTMLElement = HTMLElement>(
        selectors: string
    ): E | null;

    querySelectorAll<E extends HTMLElement = HTMLElement>(
        selectors: string
    ): NodeListOf<E>;
}

interface PromiseWithResolvers<T> {
    promise: Promise<T>;
    resolve: (value: T | PromiseLike<T>) => void;
    reject: (reason?: any) => void;
}

interface PromiseConstructor {
    withResolvers<T>(): PromiseWithResolvers<T>;
}
