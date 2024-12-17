// this is technically wrong, but in practice, it is correct. 

interface Element {
    querySelector<E extends HTMLElement = HTMLElement>(
        selectors: string
    ): E | null;

    querySelectorAll<E extends HTMLElement = HTMLElement>(
        selectors: stringj
    ): NodeListOf<E>;
}
